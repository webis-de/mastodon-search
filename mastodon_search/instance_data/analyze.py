from json import dumps, loads
from mastodon import Mastodon, MastodonAPIError, MastodonNetworkError
from math import inf
from numpy import exp
from pandas import concat, DataFrame
from scipy.stats import lognorm
from typing import TextIO
from urllib.request import urlopen

class Analyzer:
    # How many weeks are taken into account for calculation of weekly data
    num_weeks = 4

    def __init__(self, file: TextIO) -> None:
        self.data_len = 0
        self.df = None
        self.n_empty = 0
        self.n_invalid = 0

        self._load_data(file)

    def _load_data(self, file: TextIO) -> None:
        data = []
        len_raw_data = 0
        # Load raw data
        for line in file:
            len_raw_data += 1
            line_dic = loads(line)
            if not (line_dic['nodeinfo'] and line_dic['activity']):
                continue
            it = iter(line_dic['activity'])
            # The latest week is in progress and not complete.
            _ = next(it)
            for _ in range(self.num_weeks):
                activity = next(it)
                data.append({
                    'instance': line_dic['instance'],
                    'total_users':
                        line_dic['nodeinfo']['usage']['users']['total'],
                    'monthly_users':
                        line_dic['nodeinfo']['usage']['users']['activeMonth'],
                    'total_statuses':
                        line_dic['nodeinfo']['usage']['localPosts'],
                    'week_statuses': activity['statuses'],
                    'week_logins': activity['logins'],
                    'week_registrations': activity['registrations']
                })
        self.df = DataFrame(data)\
            .groupby([
                'instance', 'total_users', 'monthly_users', 'total_statuses'
            ])\
            .mean()\
            .reset_index()\
            .set_index('instance')\
            .rename(
                columns={
                    'week_statuses': 'mean_weekly_statuses',
                    'week_logins': 'mean_weekly_logins',
                    'week_registrations': 'mean_weekly_registrations'
                }
            )

        print(f'Number of fediverse instances in input file: {len_raw_data}')
        print(f'Removed for (partially) no data: {len_raw_data-len(self.df)}')
        print('↳ Almost all of these instances run fediverse software other '
            +'than Mastodon, some run Mastodon with a non-public API.')

        dupe_len_pre = len(self.df)
        self.df.index = self.df.index.str.strip('.')
        self.df = self.df[~self.df.index.duplicated(keep='first')]

        print(f'Removed duplicates: {dupe_len_pre - len(self.df)}')
        print(f'Remaining: {len(self.df)}')

    def correlate(self) -> None:
        self.delete_invalid()
        data_keys_list = list(self.df.keys())
        print('Correlation between all stats.')
        correlation = self.df.corr()
        print(correlation)
        print()
        default_stat = 'total_users'
        default_stat_index = data_keys_list.index(default_stat)
        print('Choosing', default_stat, 'as first stat per default.')
        print('Minimizing correlation of this stat plus two others…')
        correlation_sum_min = inf
        stat2_min = None
        stat3_min = None
        for stat2 in range(1, len(data_keys_list)):
            for stat3 in range(stat2):
                if (
                    (
                        corr_sum := correlation.iloc[stat2,stat3]
                                + correlation.iloc[default_stat_index,stat2]
                                + correlation.iloc[default_stat_index,stat3]
                    ) < correlation_sum_min
                ):
                    correlation_sum_min = corr_sum
                    stat2_min = stat2
                    stat3_min = stat3
        print('Minimal sum of absolute correlation values:',
            correlation_sum_min)
        print('Stats:')
        print('-', data_keys_list[stat2_min])
        print('-', data_keys_list[stat3_min])

    def delete_invalid(self) -> None:
        print('––––––––––––––––––––––––––––––––')
        len_pre = len(self.df)
        # Fake data will distort calculation:
        # 97 B (!) followers, 97 M posts on a 2-user instance
        self.df.drop('mastodon.adtension.com', inplace=True)
        self.df = self.df[~(self.df['total_statuses'] < 0)]
        print(f'Removed for invalid data (faked/negative values): {len_pre - len(self.df)}\n')

    def choose(self, out_file_prefix: str, sample_size: int = 1000) -> None:
        print('––––––––––––––––––––––––––––––––')
        cols_prob_measures = {
            col: lognorm
            for col in self.df.columns
        }
        # Estimate probability distributions over activity columns
        distributions = {
            col: dist.fit(self.df[col])
            for col, dist in cols_prob_measures.items()
        }
        # Compute normalize activity score by dividing by the estimated
        # probability.
        for col, dist in cols_prob_measures.items():
            shape, location, scale = distributions[col]
            self.df[f"{col}_log_probability"] = dist.logpdf(
                self.df[col], shape, location, scale)

        # Compute joint probability (under assumption of independence;
        # using log probabilities for numerical stability)
        self.df["log_probability"] = 0
        for col in cols_prob_measures:
            self.df["log_probability"] += self.df[f"{col}_log_probability"]

        self.df.sort_values("log_probability", inplace=True)
        self.df["weight"] = exp(-self.df["log_probability"])
        df_sample_pre = self.df.sample(
            n=SAMPLE_SIZE, replace=False, weights=self.df["weight"])

        # Remove instances that require a token for the timelines API.
        df_sample = DataFrame(columns=df_sample_pre.columns)
        deleted = []
        save_for_later = []
        tries = 0
        while (True):
            print('Testing if API is public on sample instances:')
            i=0
            to_delete = []
            len_to_test = len(df_sample_pre.index)
            for instance in df_sample_pre.index:
                mastodon = Mastodon(
                    api_base_url=instance,
                    request_timeout=30,
                    user_agent='Mastocool'
                )
                try:
                    statuses = mastodon.timeline(timeline='public')
                except MastodonAPIError:
                    deleted.append(instance)
                    to_delete.append(instance)
                except MastodonNetworkError:
                    save_for_later.append(instance)
                i += 1
                print('\r', i, '/', len_to_test, sep='', end='')
            print()
            # Retry timed out instances
            if (save_for_later):
                print('Retrying instances with timeouts…')
            while(save_for_later):
                print('\rTodo:', len(save_for_later), sep='')
                mastodon = Mastodon(
                    api_base_url=save_for_later[-1],
                    request_timeout=30,
                    user_agent='Mastocool'
                )
                try:
                    statuses = mastodon.timeline(timeline='public')
                except MastodonAPIError:
                    deleted.append(save_for_later[-1])
                    to_delete.append(save_for_later[-1])
                    save_for_later.pop()
                    tries = 0
                except MastodonNetworkError:
                    if (tries <= 3):
                        tries += 1
                    else:
                        deleted.append(save_for_later[-1])
                        to_delete.append(save_for_later[-1])
                        save_for_later.pop()
                        tries = 0
                    continue
                else:
                    save_for_later.pop()
            print()
            df_sample = concat(
                d for d in (
                    df_sample, df_sample_pre.drop(to_delete)
                ) if not d.empty
            )
            if (len(df_sample) >= SAMPLE_SIZE):
                break
            self.df.drop(df_sample_pre.index, inplace=True)
            df_sample_pre = self.df.sample(
                n=(SAMPLE_SIZE - len(df_sample)),
                replace=False,
                weights=self.df["weight"]
            )

        with open(out_file_prefix + '_removed.jsonl', mode='w+') as f:
            f.write(dumps(deleted, ensure_ascii=False))
        df_sample.sort_index(inplace=True)
        # Full DataFrame. Maybe we want to have that data later.
        df_sample.to_csv(out_file_prefix + '.csv')
        sampled_instances = df_sample.reset_index()['instance']
        # Pure instance list only.
        sampled_instances.to_csv(out_file_pure, index=False, header=False)
