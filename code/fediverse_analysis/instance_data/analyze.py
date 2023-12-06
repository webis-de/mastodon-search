from bisect import bisect_left
from json import dumps, loads
from math import inf
from random import choice, choices
from sys import exit
from typing import TextIO
import numpy as np

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
    WEEKLY_STATUSES_PU = 'weekly_statuses_per_user'
    WEEKLY_LOGINS_PU = 'weekly_logins_per_user'
    WEEKLY_REGS_PU = 'weekly_registrations_per_user'

    # How many weeks are taken into account for calculation of weekly data
    num_weeks = 4

    def __init__(self, file: TextIO) -> None:
        self.data = {
            self.TOTAL_USERS: [],
            self.MONTHLY_USERS: [],
            self.TOTAL_STATUSES: [],
            self.WEEKLY_STATUSES: [],
            self.WEEKLY_LOGINS: [],
            self.WEEKLY_REGS: [],
            self.WEEKLY_STATUSES_PU: [],
            self.WEEKLY_LOGINS_PU: [],
            self.WEEKLY_REGS_PU: []
        }
        self.data_len = 0
        self.instances = []
        self.n_empty = 0
        self.n_invalid = 0

        self._load_data(file)

    def _load_data(self, file: TextIO) -> None:
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
                self.data[self.TOTAL_USERS].append(users.get(self.TOTAL))
                self.data[self.MONTHLY_USERS].append(
                    users.get(self.MONTHLYACTIVE))
                self.data[self.TOTAL_STATUSES].append(
                    raw_data[instance].get(self.NODEINFO).get(
                        self.USAGE).get(self.LOCALPOSTS))
                self.instances.append(instance)
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
            self.data[self.WEEKLY_STATUSES].append(statuses/self.num_weeks)
            self.data[self.WEEKLY_LOGINS].append(logins/self.num_weeks)
            self.data[self.WEEKLY_REGS].append(registrations/self.num_weeks)
        self.data_len = len(raw_data)
        print(f'Total number of instances: {len_data_pre}')
        print(f'Removed for (partially) no data: {self.n_empty}')
        print(f'Removed for invalid data: {self.n_invalid}')
        print(f'Remaining: {self.data_len}')
        for i, users in enumerate(self.data[self.TOTAL_USERS]):
            if (users == 0):
                self.data[self.WEEKLY_STATUSES_PU].append(0)
                self.data[self.WEEKLY_LOGINS_PU].append(0)
                self.data[self.WEEKLY_REGS_PU].append(0)
            else:
                self.data[self.WEEKLY_STATUSES_PU].append(
                    self.data[self.WEEKLY_STATUSES][i] / users)
                self.data[self.WEEKLY_LOGINS_PU].append(
                    self.data[self.WEEKLY_LOGINS][i] / users)
                self.data[self.WEEKLY_REGS_PU].append(
                    self.data[self.WEEKLY_REGS][i] / users)

    def correlate(self) -> None:
        print('––––––––––––––––––––––––––––––––')
        print('Available statistics (stats):')
        data_keys_list = list(self.data.keys())
        print(data_keys_list)
        print()
        print('Correlation between these stats. Each row and column '
            +'represents one statistic, starting from the top left corner in '
            +'the order of the above list.')
        np.set_printoptions(formatter={'float_kind':"{:.4f}".format})
        correlation = np.corrcoef(list(self.data.values()))
        print(correlation)
        print()
        default_stat = self.TOTAL_USERS
        default_stat_index = data_keys_list.index(default_stat)
        print('Choosing', default_stat, 'as first stat per default.')
        print('Minimizing correlation of this stat plus two others…')
        abs_correlation = abs(correlation)
        correlation_sum_min = inf
        stat2_min = None
        stat3_min = None
        for stat2 in range(1, len(self.data.keys())):
            for stat3 in range(stat2):
                if ((corr_sum := abs_correlation[stat2][stat3]
                                + abs_correlation[default_stat_index][stat2]
                                + abs_correlation[default_stat_index][stat3]
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

    def stratify(self,
        sample_file: TextIO,
        data_file: TextIO,
        sample_size: int = 1000
    ) -> None:
        sample = {}
        stats_to_stratify = [self.TOTAL_USERS, self.WEEKLY_LOGINS_PU,
            self.TOTAL_STATUSES]
        data_to_stratify = np.array([])
        bucket_cutoffs = [[] for _ in range(len(stats_to_stratify))]
        data_to_stratify = np.array(
            [self.data[stat] for stat in stats_to_stratify])

        print('––––––––––––––––––––––––––––––––')
        print('Statistics (stats) to do stratified sampling on:')
        # First, calculate bucket cutoff values
        # Logarithmic distributions
        for i in range(len(data_to_stratify)):
            minimum = min(data_to_stratify[i])
            maximum = max(data_to_stratify[i])
            print(stats_to_stratify[i])
            print('  min:', minimum)
            print('  max:', maximum)
            # Handle 0 separately as it will always contain somme instances.
            cutoff = 0.0001
            last_cutoff = 0
            while (cutoff < maximum):
                indices = np.where(data_to_stratify[i][
                        np.where(data_to_stratify[i] > last_cutoff)
                    ] <= cutoff)
                last_cutoff = cutoff
                cutoff *= 10
                if (len(indices[0]) == 0):
                    continue
                bucket_cutoffs[i].append(last_cutoff)
            print('  bucket cut-offs:', end='')
            print(bucket_cutoffs[i])

        # Create buckets. It's 4d, because each bucket itself is a dict.
        bucketed_data = [
            [
                [
                    {} for _ in range(len(bucket_cutoffs[2]) + 1)
                ] for _ in range(len(bucket_cutoffs[1]) + 1)
            ] for _ in range(len(bucket_cutoffs[0]) + 1)
        ]
        # Put instances into buckets. E. g.: bucketed_data[x][y][z]
        for i, instance in enumerate(self.instances):
            x = bisect_left(bucket_cutoffs[0], data_to_stratify[0][i])
            y = bisect_left(bucket_cutoffs[1], data_to_stratify[1][i])
            z = bisect_left(bucket_cutoffs[2], data_to_stratify[2][i])
            bucketed_data[x][y][z][instance] = {
                stat: data_to_stratify[j][i] for
                    j, stat in enumerate(stats_to_stratify)
            }
        # Sample from buckets
        # One from each bucket
        for i in range(len(bucketed_data)):
            for j in range(len(bucketed_data[i])):
                for k in range(len(bucketed_data[j])):
                    if (bucketed_data[i][j][k]):
                        item = choice(list(bucketed_data[i][j][k].keys()))
                        sample[item] = bucketed_data[i][j][k][item]
                        del bucketed_data[i][j][k][item]
        # Proportional sampling
        factor = min(1, (sample_size-len(sample)) / self.data_len)
        for i in range(len(bucketed_data)):
            for j in range(len(bucketed_data[i])):
                for k in range(len(bucketed_data[j])):
                    if (bucketed_data[i][j][k]):
                        num = len(bucketed_data[i][j][k]) * factor
                        items = choices(
                            list(bucketed_data[i][j][k].keys()), k=round(num))
                        for item in items:
                            sample[item] = bucketed_data[i][j][k][item]
        if (sample_file):
            for instance in sample:
                sample_file.write(instance + '\n')
            print('Sample size:', len(sample))
        else:
            for instance in sample:
                print(instance)
        if (data_file):
            data_file.write(dumps(bucketed_data))
