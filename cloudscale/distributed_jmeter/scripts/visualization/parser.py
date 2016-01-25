#
#  Copyright (c) 2015 XLAB d.o.o.
#  All rights reserved. This program and the accompanying materials
#  are made available under the terms of the Eclipse Public License v1.0
#  which accompanies this distribution, and is available at
#  http://www.eclipse.org/legal/epl-v10.html
#
import datetime
import os
import re
import time
import csv
import calendar
import sys

from dateutil import parser
import pandas as pd

from cloudscale.distributed_jmeter.scripts.visualization.SLO import SLO
from cloudscale.distributed_jmeter.scripts.visualization.converters import Converters


class Parse:
    def __init__(self, num_threads, duration):
        self.num_threads = num_threads
        self.duration = duration
        self.max_time = SLO

    def does_violate_slo(self, url, estimated_time, response_code):
        try:
            return not (int(estimated_time) < self.max_time[url] and response_code == 200)
        except KeyError as e:
            print "There's no SLO for %s" % url

    def get_instances_lifetime(self, as_file):
        instance_ids = []
        instances = []
        launched_instances, terminated_instances = self._read_autoscalability(as_file)

        #is_dst = time.daylight and time.localtime().tm_isdst > 0
        #utc_offset = - (time.altzone if is_dst else time.timezone)

        for instance in launched_instances:
            instance['start_time'] = instance['end_time'] # + datetime.timedelta(hours=utc_offset / 3600)
            instance['end_time'] = None

            terminated_instance, _ = self._find_instance(instance, terminated_instances)
            if terminated_instance:
                _, i = self._find_instance(instance, instances)
                if i is None:
                    instance['end_time'] = terminated_instance['start_time']
                    instances.append(instance)
                else:
                    instances[i]['end_time'] = terminated_instance['start_time']
            else:
                # instance['end_time'] = terminated_instance['start_time']
                instances.append(instance)

        min_date = self.data['date'].min().to_datetime()
        max_date = self.data['date'].max().to_datetime()
        for instance in instances:
            if instance['start_time'] < min_date:
                instance['start_time'] = min_date

            if instance['end_time'] is None:
                instance['end_time'] = max_date
        return instances

    def _find_instance(self, instance, terminated_instances):
        for i in xrange(len(terminated_instances)):
            ins = terminated_instances[i]
            if ins['id'] == instance['id']:
                return ins, i
        return None, None

    def _read_autoscalability(self, as_file):
        launched_instances = []
        terminated_instances = []
        with open(as_file) as fp:
            next(fp)  # skip the header
            for line in fp:
                line = line[:-1]
                instance_id, start_time, end_time, action = line.split(',')

                instance = {}
                instance['id'] = instance_id
                instance['action'] = action
                instance['start_time'] = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                instance['end_time'] = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")

                if action == 'launch':
                    launched_instances.append(instance)
                if action == 'terminate':
                    terminated_instances.append(instance)
        return launched_instances, terminated_instances

    def delete_records_that_violates_slo(self, output_file, input_file):
        converters = Converters()
        with open(output_file, 'w') as slo_fp:
            slo_fp.write('"date","response_time","url","response_code","status","autoscalable","instance_id"\n')
            with open(input_file) as fp:
                next(fp)  # skip header
                for line in fp:
                    timestamp, estimated_time, url, response_code, status, attr1, attr2 = line.split(",")
                    response_code = converters.response_code_converter(response_code)
                    if self.does_violate_slo(url, estimated_time, response_code):
                        slo_fp.write('%s,%s,%s,%s,%s,%s,%s' % (
                            timestamp, estimated_time, url, response_code, status, attr1, attr2))

    def slo_agg_seconds(self, parsed_file, jmeter_log_file, output_file, seconds, skip=0):
        print "Parsing for %s seconds" % seconds
        with open(output_file, 'w') as slo_fp:
            with open(parsed_file) as fp:
                next(fp)  # skip header
                parsed_file_data = csv.reader(fp)
                sorted_data = sorted(parsed_file_data, key=lambda row: int(row[0]))

                ref_timestamp = self._get_ref_timestamp(jmeter_log_file) + seconds
                timestamps = self._calc_slo_violations(sorted_data, ref_timestamp, seconds)

                vus_when_violates, interval_when_violates = self._write_file(slo_fp, timestamps, ref_timestamp, seconds, skip)
                return vus_when_violates, interval_when_violates

    def _calc_slo_violations(self, sorted_data, ref_timestamp, seconds):
        converters = Converters()
        timestamps = {ref_timestamp: {'num': 0, 'num_all_requests': 0}}
        for line in sorted_data:
            timestamp, estimated_time, url, response_code, status, attr1, attr2 = line
            timestamp = (int(timestamp) / 1000)
            response_code = converters.response_code_converter(response_code)

            if ref_timestamp - timestamp < 0:
                ref_timestamp = ref_timestamp + seconds
                if not timestamps.has_key(ref_timestamp):
                    timestamps[ref_timestamp] = {'num': 0, 'num_all_requests': 0}

            timestamps[ref_timestamp]['num_all_requests'] += 1
            timestamps[ref_timestamp]['num'] += 1 if self.does_violate_slo(url, estimated_time, response_code) else 0

        return timestamps


    def _write_file(self, fp, timestamps, min_date, seconds, skip):
        content = '"date","datetime","num","num_all_requests", "percent_slo", "theorethical_requests", "requests_per_interval", "vus", "when_violates"\n'
        content += '%s,%s,%s,%s,%s,%s,%s,%s,%s\n' % (0, 0, 0, 0, 0, 0, 0, 0, '')

        vus_when_violates = 0
        interval_when_violates = 0
        i = 0
        violates = False
        sorted_keys = sorted(timestamps.keys())
        for timestamp in sorted_keys:
            if i > skip:
                num_slo = timestamps[timestamp]['num']
                num_all_req = timestamps[timestamp]['num_all_requests']
                percent_slo = self._calc_slo_percentage(num_slo, num_all_req)
                theorethical_requests = self._calc_theorethical_requests(i, self.duration, self.num_threads, seconds)
                vus = self._calc_vus(i, self.num_threads, self.duration, seconds)
                does_violates = self._calc_when_violates(sorted_keys, timestamps, i, violates)

                requests_per_interval = self._calc_ideal_increase(i, self.duration, seconds, self.num_threads)

                violates_str = ''
                if does_violates:
                    violates = True
                    vus_when_violates = vus
                    interval_when_violates = i
                    violates_str = 'req. = %s (%s) / VU = (%s)' % (int(theorethical_requests), num_all_req, vus)

                timestamp_subtract = (timestamp - min_date) + seconds

                content += '%s,%s,%s,%s,%s,%s,%s,%s,%s\n' % \
                           (
                               timestamp_subtract * 1000,
                               datetime.datetime.fromtimestamp(timestamp),
                               num_slo,
                               num_all_req,
                               percent_slo,
                               theorethical_requests,
                               requests_per_interval,
                               vus,
                               violates_str
                           )
            i += 1

        fp.write(content)
        return vus_when_violates, interval_when_violates

    def _calc_ideal_increase(self, i, duration, seconds, num_threads):
        scenario_duration_in_sec = duration*60
    	requests_per_second = (num_threads/7)
        requests_per_scenario = requests_per_second * scenario_duration_in_sec
        requests_per_duration = requests_per_scenario/(scenario_duration_in_sec/seconds)
        num_intervals = scenario_duration_in_sec/seconds
        inc = requests_per_duration/(num_intervals+1)

        return (i+1)*inc

    def _calc_when_violates(self, keys, timestamps, i, violates):
        timestamp = keys[i]
        if i+1 < len(timestamps):
            timestamp = keys[i+1]

        num_slo = timestamps[timestamp]['num']
        num_all_req = timestamps[timestamp]['num_all_requests']
        percent_slo = self._calc_slo_percentage(num_slo, num_all_req)
        does_violate = False
        if not violates and percent_slo != '' and float(percent_slo) > 10:
            does_violate = True
        return does_violate

    def _calc_vus(self, i, num_threads, duration, seconds):
        threads_per_minute = num_threads / ((duration * 60.0) / seconds)
        return round((i*threads_per_minute + (i+1) *threads_per_minute)/2)

    def _calc_theorethical_requests(self, i, duration, num_threads, seconds):
        # '''
        # x os = cas
        # y os = requesti
        #
        # vus = 14000
        # dolzina scenarija = 960 sec (16 min)
        #
        # 1.  Koliko requestov v naredimo v 7 sekundah, ce podatke aggregiramo na 60, 10, 5 sec?
        #     60/7 = 8.52
        #     10/7 = 1.42
        #     5/7 = 0.71
        #
        # 2.  Spravimo prejsne vrednosti na isto skalo, t.j. koliko requestov naredimo na minuto ce aggregiramo podatke na 60, 10 in 5 sec?
        #     8.52 * (60/60) = 8.57 requestov/min
        #     1.42 * (60/10) = 8.52 requestov/min
        #     0.71 * (60/5) = 8.52 requestov/min
        #
        # 3.  Stopnja povecevanja VUjev na sekundo je:
        #     14000/960 = 14,5
        #
        # 4.  Na aggregacijsko enoto (60, 10 in 5 sec) naredimo:
        #
        #     8.57 * 14,5 * 60 = 7455,9 requestov/min
        #     8.52 * 14,5 * 10 = 1235,4 requestov/min
        #     8.52 * 14.5 * 5 = 617.7 requestov/min
        #
        # 5.  Delimo vrednost z 2, da dobimo povprecje
        #
        # '''
        # requests_per_agg = seconds/7.0
        # print requests_per_agg
        # requests_per_min = requests_per_agg * (60/seconds)
        # print requests_per_min
        # inc_rate = num_threads/(duration*60)
        # print inc_rate
        # requests_per_interval = requests_per_min * inc_rate * seconds
        # print requests_per_interval

        scenario_duration_in_sec = duration * 60
        requests_per_second = num_threads / 7
        num_intervals = int(scenario_duration_in_sec) / seconds

        requests_per_interval = requests_per_second * seconds * 1.0
        requests_per_duration = requests_per_interval / num_intervals
        r = int(((i) * requests_per_duration) + ((i+1) * requests_per_duration)) / 2
        return r

    def _calc_slo_percentage(self, num_slo, num_all_req):
        percent_slo = ""
        if num_slo > 0:
            percent = (num_slo * 100.0) / num_all_req
            percent_slo = "%.2f" % percent

        return percent_slo

    def _get_ref_timestamp(self, jmeter_log_file):
        with open(jmeter_log_file, 'r') as fp:
            for line in fp:
                if re.search('jmeter.threads.JMeterThread: Running PostProcessors in forward order', line):
                    m = re.search("([0-9]{4}/[0-9]{2}/[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}) INFO", line)
                    d = parser.parse("%s UTC" % m.group(1))
                    t = calendar.timegm(d.timetuple())
                    return t

    def _find_min_date(self, data):
        min_date = sys.maxint
        for row in data:
            if int(row[0]) < min_date:
                min_date = min_date

        return min_date

    def merge(self, output_file, as_file, file):

        response_time_stack = []
        epoch = datetime.datetime(1970, 1, 1)
        with open(output_file, 'w') as m_fp:
            m_fp.write('"date","response_time","url","response_code","status","attr1","attr2","instance_id","y"\n')
            if os.path.exists(as_file):
                instances = self.get_instances_lifetime(as_file)
                i = -5
                for instance in instances:
                    instance_id = instance['id']
                    start_date = datetime.datetime(1970, 1, 1)
                    end_date = datetime.datetime.now()
                    with open(file) as fp:
                        next(fp)  # skip the header
                        for line in fp:
                            timestamp, estimated_time, url, response_code, status, attr1, attr2 = line.split(",")
                            dt = datetime.datetime.fromtimestamp(int(timestamp) / 1000.0)

                            if dt <= instance['start_time'] and dt > start_date:
                                start_date = dt
                                start_string = '%s,%s,%s,%s,%s,%s,%s,%s,%s\n' % (
                                    timestamp, estimated_time, url, response_code, status, attr1, attr2[:-1],
                                    instance_id,
                                    i)

                            if dt >= instance['end_time'] and dt < end_date:
                                end_date = dt
                                end_string = '%s,%s,%s,%s,%s,%s,%s,%s,%s\n' % (
                                    timestamp, estimated_time, url, response_code, status, attr1, attr2[:-1],
                                    instance_id,
                                    i)
                    m_fp.write(start_string)
                    m_fp.write(end_string)
                    i -= 5

    def timestamp_to_datetime_file(self):
        with open('files/response-times-over-time.trans.tab', 'w') as fp_out:
            fp_out.write('timestamp\tdate\tresponse_time\turl\tresponse_code\tstatus\n')
            fp_out.write('c\td\tc\ts\td\td\n')
            with open(self.file) as fp:
                next(fp)  # skip the header
                for line in fp:
                    ts, curr_dt, response_time, url, response_code, status = self.parse_line(line)
                    fp_out.write('%s\t%s\t%s\t%s\t%s\t%s\n' % (
                        ts, curr_dt.strftime('%H:%M'), response_time, url, response_code, status))

    def get_end_time(self, instance_id, instances):
        i = 0
        for instance in instances:
            if instance['id'] == instance_id:
                break
            i += 1
        try:
            end_time = instances[i + 1]['start_time']
            return end_time
        except IndexError as e:
            return self.data['date'].max().to_datetime()

    def parse_line(self, line):
        ts, response_time, url, response_code, status, _, _ = line.split(",")
        dt = datetime.datetime.fromtimestamp(int(ts) / 1000.0)
        rc = self.parse_response_code(response_code)

        return ts, dt, int(response_time), str(url), rc, str(status)

    def parse_response_code(self, rc):
        try:
            return int(rc)
        except:
            return 500

    def parse(self, output_file, file):
        with open(file) as fp:
            next(fp)  # skip the header
            with open(output_file, "w") as parsed_fp:
                parsed_fp.write("date,response_time,url,response_code,status,attr1,attr2\n")
                converters = Converters()
                for line in fp:
                    timestamp, estimated_time, url, response_code, status, attr1, attr2 = line.split(",")
                    response_code = converters.response_code_converter(response_code)
                    url = converters.url_converter(url)
                    if url is not None:
                        parsed_fp.write('%s,%s,%s,%s,%s,%s,%s' % (
                            timestamp, estimated_time, url, response_code, status, attr1, attr2))

    def to_dataframe(self, file, as_file):


        print "Parsing " + file
        converters = Converters()
        self.data_indexed = pd.read_csv(file, index_col='date', converters={
            'date': converters.timestamp_converter,
            'response_code': converters.response_code_converter,
            'url': converters.url_converter
        })

        self.data = pd.read_csv(file, converters={
            'date': converters.timestamp_converter,
            'response_code': converters.response_code_converter,
            'url': converters.url_converter
        })


        # print "Parsing " + as_file
        # self.autoscalability_data = pd.read_csv(as_file, converters={
        #     'start_time' : converters.datetime_to_timestamp,
        #     'end_time' : converters.datetime_to_timestamp,
        #     'action' : converters.action_to_number
        # })
        return

    def merge_autoscaling(self, file1, file2):
        pass

    def write_file_when_violates(self, vus60, interval_when_violates, vus10, vus5, ec2_file, rds_cpu_file, output_file):
        cpu_ec2_when_violates = self._get_cpu_util_when_violates(ec2_file, interval_when_violates)
        cpu_rds_when_violates = self._get_cpu_util_when_violates(rds_cpu_file, interval_when_violates)

        with open(output_file, "w") as fp:
            fp.write("DBU 1m = %s\n" % cpu_rds_when_violates)
            fp.write("FU 1m = %s\n" % cpu_ec2_when_violates)
            fp.write("VU 1m = %s\n" % vus60)
            fp.write("VU 10s = %s\n" % vus10)
            fp.write("VU 5s = %s\n" % vus5)

    def _get_cpu_util_when_violates(self, file, interval_when_violates):
        with open(file, 'r') as fp:
            try:
                next(fp)
                timestamps = {}
                for line in fp:
                    instance_id, timestamp, average = line.split(',')
                    if not timestamps.has_key(timestamp):
                        timestamps[timestamp] = {}
                        timestamps[timestamp]['sum'] = float(average)
                        timestamps[timestamp]['num'] = 1

                    timestamps[timestamp]['sum'] += float(average)
                    timestamps[timestamp]['num'] += 1

                sorted_keys = sorted(timestamps)
                timestamp_when_violates = sorted_keys[interval_when_violates]
                cpu_utilisation = timestamps[timestamp_when_violates]['sum']/timestamps[timestamp_when_violates]['num']
                return cpu_utilisation
            except IndexError as e:
                return None