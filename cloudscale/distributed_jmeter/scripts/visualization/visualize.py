import os
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
        self.slo_violations_non_agg_file = base_filename + ".slo_non_agg.csv"
        self.slo_violations_agg = base_filename + ".slo_agg.csv"
        self.slo_violations_agg_1second = base_filename + ".slo_agg_1second.csv"
        self.slo_violations_agg_5seconds = base_filename + ".slo_agg_5seconds.csv"
        self.slo_violations_agg_10seconds = base_filename + ".slo_agg_10seconds.csv"
        self.ec2_file = path + "/ec2-cpu.csv"
        self.rds_cpu_file = path + "/rds-cpu.csv"

        data = Parse()
        data.parse(self.parsed_file, self.main_file)
        data.to_dataframe(self.parsed_file, autoscaling_file)
        data.merge(self.merged_file, autoscaling_file, self.parsed_file)
        data.delete_records_that_violates_slo(self.slo_violations_non_agg_file, self.parsed_file)
        data.slo_agg_seconds(self.parsed_file, self.slo_violations_agg, 60)
        data.slo_agg_seconds(self.parsed_file, self.slo_violations_agg_1second, 1)
        data.slo_agg_seconds(self.parsed_file, self.slo_violations_agg_5seconds, 5)
        data.slo_agg_seconds(self.parsed_file, self.slo_violations_agg_10seconds, 10)

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
                       self.rds_cpu_file)

    def save(self):
        return ""

def run_multiple(vus, path):
    R_FILE = '/Volumes/Storage/Xlab/cloudscale/gitlab/distributed-jmeter-standalone/cloudscale/distributed_jmeter/scripts/visualization/r_visualization.R'

    IDS = os.listdir(path)
    for id in IDS:
        if os.path.isdir("%s/%s" % (path, id)):
            try:
                MAIN_FILE = "%s%s/response-times-over-time.csv" % (path, id)
                print MAIN_FILE
                AUTOSCALING_FILE = "%s/%s/autoscalability.csv" % (path, id)
                shutil.copy2(R_FILE, os.path.dirname(MAIN_FILE))
                run_single(vus, MAIN_FILE, AUTOSCALING_FILE, R_FILE)
            except Exception as e:
                import traceback
                print traceback.format_exc()
                continue

def run_single(vus, duration, main_file, autoscaling_file, r_file):

    shutil.copy2(r_file, os.path.dirname(main_file))

    v = Visualize(vus, duration, r_file, main_file, autoscaling_file)
    path = v.save()

    print path

if __name__ == "__main__":

    # path = "/Users/ivansek/Desktop/AWS measurements - 2.2.2015/"
    # run_multiple(10000, path)
    PATH = '/Volumes/Storage/Xlab/cloudscale/gitlab/distributed-jmeter-standalone/bin/results/df52f3b9-3de6-4129-bb03-425797758b53'
    # PATH = '/Volumes/Storage/Xlab/cloudscale/gitlab/distributed-jmeter-standalone/bin/6c346f9c-0aef-44f5-88fe-54c92788ab19'
    MAIN_FILE = '%s/response-times-over-time.csv' % PATH
    AUTOSCALING_FILE = '%s/autoscalability.log' % PATH
    R_FILE = '/Volumes/Storage/Xlab/cloudscale/gitlab/distributed-jmeter-standalone/cloudscale/distributed_jmeter/scripts/visualization/r_visualization.R'
    run_single(4000, 16, MAIN_FILE, AUTOSCALING_FILE, R_FILE)