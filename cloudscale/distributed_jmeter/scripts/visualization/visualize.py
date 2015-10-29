import os
import re
import shutil

from plotter import Plot
from cloudscale.distributed_jmeter.scripts.visualization.parser import Parse


class Visualize:

    def __init__(self, num_threads, duration, r_file, main_file, autoscaling_file):
        base_filename = main_file[:-4]
        path = os.path.dirname(main_file)

        self.main_file = main_file
        self.parsed_file = base_filename + ".parsed.csv"
        self.merged_file = base_filename + ".merged.csv"
        self.jmeter_log_file = path + '/scenario.log'
        self.slo_violations_non_agg_file = base_filename + ".slo_non_agg.csv"
        self.slo_violations_agg = base_filename + ".slo_agg.csv"
        self.slo_violations_agg_1second = base_filename + ".slo_agg_1second.csv"
        self.slo_violations_agg_5seconds = base_filename + ".slo_agg_5seconds.csv"
        self.slo_violations_agg_10seconds = base_filename + ".slo_agg_10seconds.csv"
        self.ec2_file = path + "/ec2-cpu.csv"
        self.rds_cpu_file = path + "/rds-cpu.csv"
        self.output_dir = path + "/graphs"
        self.report_file = path + "/graphs/report.txt"
        print self.output_dir
        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)


        data = Parse(num_threads, duration)
        data.parse(self.parsed_file, self.main_file)
        data.to_dataframe(self.parsed_file, autoscaling_file)
        data.merge(self.merged_file, autoscaling_file, self.parsed_file)
        data.delete_records_that_violates_slo(self.slo_violations_non_agg_file, self.parsed_file)
        vus60, interval = data.slo_agg_seconds(self.parsed_file, self.jmeter_log_file, self.slo_violations_agg, 60)
        vus10, _ = data.slo_agg_seconds(self.parsed_file, self.jmeter_log_file, self.slo_violations_agg_10seconds, 10, skip=10)
        vus5, _ = data.slo_agg_seconds(self.parsed_file, self.jmeter_log_file, self.slo_violations_agg_5seconds, 5, skip=20)
        data.write_file_when_violates(vus60, interval, vus10, vus5, self.ec2_file, self.rds_cpu_file, self.report_file)

        plotter = Plot(num_threads, duration, r_file,
                       self.main_file,
                       self.parsed_file,
                       self.merged_file,
                       self.slo_violations_agg,
                       self.slo_violations_non_agg_file,
                       autoscaling_file,
                       self.slo_violations_agg_1second,
                       self.slo_violations_agg_5seconds,
                       self.slo_violations_agg_10seconds,
                       self.ec2_file,
                       self.rds_cpu_file,
                       self.output_dir)

    def save(self):
        return ""

def run_multiple(path):
    R_FILE = '/Volumes/Storage/Xlab/cloudscale/gitlab/distributed-jmeter-standalone/cloudscale/distributed_jmeter/scripts/visualization/r_visualization.R'

    IDS = os.listdir(path)
    for id in IDS:
        if os.path.isdir("%s/%s" % (path, id)):
            try:
                MAIN_FILE = "%s/%s/response-times-over-time.csv" % (path, id)
                R_NEW_FILE = "%s/%s/r_visualization_new.R" % (path, id)
                print MAIN_FILE
                AUTOSCALING_FILE = "%s/%s/autoscalability.csv" % (path, id)
                shutil.copy2(R_FILE, os.path.dirname(MAIN_FILE))
                vus, duration = get_vus_duration_from(R_NEW_FILE)
                print "vus = %s, duration = %s" % (vus, duration)
                run_single(vus, duration, MAIN_FILE, AUTOSCALING_FILE, R_FILE)
            except Exception as e:
                import traceback
                print traceback.format_exc()
                continue

def get_vus_duration_from(r_new_file):
    with open(r_new_file, 'r') as fp:
        ''' First two lines contains the number of vus and duration '''
        vus_row = fp.next()
        duration_row = fp.next()

        vus_m = re.search('num_threads ?<- ?([0-9]+)', vus_row)
        duration_m = re.search('scenario_duration_in_min ?<- ?([0-9]+)', duration_row)

        return int(vus_m.group(1)), int(duration_m.group(1))



def run_single(vus, duration, main_file, autoscaling_file, r_file):

    shutil.copy2(r_file, os.path.dirname(main_file))

    v = Visualize(vus, duration, r_file, main_file, autoscaling_file)
    path = v.save()

    print path

if __name__ == "__main__":
    #
    # path = "/Volumes/Storage/Xlab/cloudscale/measurement-results/Split-tresholds-27.6.2015/"
    # run_multiple(path)
    ID = '27782521-5ef1-45f7-93d9-e6fe89610d4a'
    PATH = '/Volumes/Storage/Xlab/projects/cloudscale/gitlab/distributed-jmeter-standalone/bin/results/%s/' % ID
    # PATH = '/Volumes/Storage/Xlab/cloudscale/gitlab/distributed-jmeter-standalone/bin/6c346f9c-0aef-44f5-88fe-54c92788ab19'
    MAIN_FILE = '%s/response-times-over-time.csv' % PATH
    AUTOSCALING_FILE = '%s/autoscalability.log' % PATH
    R_FILE = '/Volumes/Storage/Xlab/projects/cloudscale/gitlab/distributed-jmeter-standalone/cloudscale/distributed_jmeter/scripts/visualization/r_visualization.R'
    import datetime
    start_time = datetime.datetime.now()
    run_single(10000, 120, MAIN_FILE, AUTOSCALING_FILE, R_FILE)
    print datetime.datetime.now()-start_time