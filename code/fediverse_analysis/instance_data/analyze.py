from json import loads
from math import inf
from pandas import DataFrame
from typing import TextIO

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
            if not (line_dic['nodeinfo']
                    and line_dic['activity']):
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
            .groupby(['instance', 'total_users', 'monthly_users', 'total_statuses'])\
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
        print(f'Total number of instances: {len_raw_data}')
        print(f'Removed for (partially) no data: {len_raw_data - len(self.df)}')
        print(f'Remaining: {len(self.df)}')

    def correlate(self) -> None:
        print('––––––––––––––––––––––––––––––––')
        self.delete_invalid()
        print()
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
                if ((corr_sum := correlation.iloc[stat2,stat3]
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
        # "localPosts": 97009982
        self.df.drop('mastodon.adtension.com')
        # "localPosts": -1243
        self.df.drop('linuxjobs.social')
        self.n_invalid += 2
        print(f'Removed for invalid data: {self.n_invalid}')

    def stratify(self, out_file: TextIO) -> None:
        # Stats to apply quantile sampling on.
        stats = ['total_users', 'total_statuses', 'mean_weekly_statuses']
        # Labels for the columns to be inserted
        labels = ['percentile_'+stat for stat in stats]
        # Drop columns we don't need so we can use df instead of df[…].
        self.df.drop(
            self.df.columns.difference(stats),
            axis='columns', inplace=True
        )
        # Stat 1: Sort
        self.df.sort_values(stats[0], inplace=True)
        # Add a rolling count.
        self.df.insert(0, labels[0], range(len(self.df)))
        # Compute that to discrete integers: 0–9.
        self.df[labels[0]] = 10 * self.df[labels[0]] // len(self.df)
        # Do stat 2: Sort inside of groups of first stat percentiles.
        self.df = self.df.groupby(labels[0], as_index=False).apply(
            lambda x: x.sort_values(stats[1]))
        # Add a rolling count inside of each group.
        self.df.insert(
            1, labels[1],
            self.df.groupby(
                (self.df[labels[0]] != self.df[labels[0]].shift(1)).cumsum()
            ).cumcount()
        )
        # Get the size of each subgroup.
        group_sizes = self.df.groupby(labels[0]).size()
        # Compute the count per group to integers 0–9.
        # This groupby operation takes a few seconds.
        self.df[labels[1]] = self.df.groupby([labels[0], labels[1]])\
            .apply(lambda x: x[labels[1]] * 10
                            // group_sizes[x[labels[1]].index[0][0]])\
            .droplevel([0, 1])
        self.df = self.df.droplevel(0)
        # Do stat 3: Pretty much the same as stat 2.
        self.df = self.df.groupby(
            [labels[0], labels[1]], as_index=False).apply(
                lambda x: x.sort_values(stats[2]))
        self.df.insert(
            2, labels[2],
            self.df.groupby(
                (self.df[labels[1]] != self.df[labels[1]].shift(1)).cumsum()
            ).cumcount()
        )
        group_sizes = self.df.groupby(
            [labels[0], labels[1]], as_index=False).size()['size']
        # Again, this groupby operation takes a few seconds.
        self.df[labels[2]] = self.df.groupby([labels[0], labels[1], labels[2]])\
            .apply(lambda x: x[labels[2]] * 10
                            // group_sizes[x[labels[2]].index[0][0]]\
            ).droplevel([0, 1, 2])
        self.df = self.df.droplevel(0)

        sample = self.df.groupby(labels).sample(1)
        sample.to_csv(out_file)
