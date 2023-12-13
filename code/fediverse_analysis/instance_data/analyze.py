from bisect import bisect_left
from json import dumps, loads
from math import inf
from random import choice, choices
from sys import exit
from typing import TextIO
import pandas as pd

class Analyzer:
    ACTIVITY = 'activity'
    LOCALPOSTS = 'localPosts'
    LOGINS = 'logins'
    MONTHLYACTIVE = 'activeMonth'
    NODEINFO = 'nodeinfo'
    REGISTRATIONS = 'registrations'
    STATS = 'stats'
    STATUSES = 'statuses'
    TOTAL = 'total'
    USAGE = 'usage'
    USERCOUNT = 'user_count'
    USERS = 'users'
    WEEK = 'week'

    TOTAL_USERS = 'total_users'
    MONTHLY_USERS = 'monthly_users'
    TOTAL_STATUSES = 'total_statuses'
    WEEKLY_STATUSES = 'weekly_statuses'
    WEEKLY_LOGINS = 'weekly_logins'
    WEEKLY_REGS = 'weekly_registrations'

    # How many weeks are taken into account for calculation of weekly data
    num_weeks = 4

    def __init__(self, file: TextIO) -> None:
        self.data_len = 0
        self.df = None
        self.n_empty = 0
        self.n_invalid = 0

        self._load_data(file)

    def _load_data(self, file: TextIO) -> None:
        data = {
            self.TOTAL_USERS: [],
            self.MONTHLY_USERS: [],
            self.TOTAL_STATUSES: [],
            self.WEEKLY_STATUSES: [],
            self.WEEKLY_LOGINS: [],
            self.WEEKLY_REGS: [],
        }
        instances = []
        raw_data = dict()
        try:
            # Load raw data
            for line in file:
                line_data = line.split(' ', maxsplit=1)
                if(line_data[1].strip()):
                    raw_data[line_data[0]] = loads(line_data[1])
                else:
                    raw_data[line_data[0]] = None
        except Exception as e:
            print(e)
            exit(1)
        # Count how many we remove for what reason and the overall number
        len_data_pre = len(raw_data)
        # "localPosts": 97009982
        del raw_data['mastodon.adtension.com']
        # "localPosts": -1243
        del raw_data['linuxjobs.social']
        self.n_invalid += 2
        # List is needed so we can change dict's size during iteration.
        for instance in list(raw_data.keys()):
            # Remove empty-valued entries (i. e. from non-Mastodon instances)
            if not (raw_data[instance]) or not (
                    raw_data[instance].get(self.NODEINFO)
                    and raw_data[instance].get(self.ACTIVITY)
            ):
                del raw_data[instance]
                self.n_empty += 1
                continue
            if (users := raw_data[instance].get(self.NODEINFO).get(
                    self.USAGE).get(self.USERS)):
                data[self.TOTAL_USERS].append(users.get(self.TOTAL))
                data[self.MONTHLY_USERS].append(
                    users.get(self.MONTHLYACTIVE))
                data[self.TOTAL_STATUSES].append(
                    raw_data[instance].get(self.NODEINFO).get(
                        self.USAGE).get(self.LOCALPOSTS))
                instances.append(instance)
            else:
                del raw_data[instance]
                self.n_invalid += 1
                continue
            it = iter(raw_data[instance].get(self.ACTIVITY))
            # The latest week is in progress and not complete.
            _ = next(it)
            statuses = 0
            logins = 0
            registrations = 0
            # Some servers don't give us much more than 4 weeks of data.
            for i in range(self.num_weeks):
                activity_data = next(it)
                statuses += activity_data.get(self.LOGINS)
                logins += activity_data.get(self.STATUSES)
                registrations += activity_data.get(self.REGISTRATIONS)
            data[self.WEEKLY_STATUSES].append(statuses/self.num_weeks)
            data[self.WEEKLY_LOGINS].append(logins/self.num_weeks)
            data[self.WEEKLY_REGS].append(registrations/self.num_weeks)
        self.df = pd.DataFrame(data, index=instances)
        self.data_len = len(raw_data)
        print(f'Total number of instances: {len_data_pre}')
        print(f'Removed for (partially) no data: {self.n_empty}')
        print(f'Removed for invalid data: {self.n_invalid}')
        print(f'Remaining: {self.data_len}')

    def correlate(self) -> None:
        print('––––––––––––––––––––––––––––––––')
        print('Available statistics (stats):')
        data_keys_list = list(self.df.keys())
        print(data_keys_list)
        print()
        print('Correlation between these stats.')
        correlation = self.df.corr()
        print(correlation)
        print()
        default_stat = self.TOTAL_USERS
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

    def stratify(self, out_file: TextIO) -> None:
        # Stats to apply quantile sampling on.
        stats = [self.TOTAL_USERS, self.TOTAL_STATUSES, self.WEEKLY_STATUSES]
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
