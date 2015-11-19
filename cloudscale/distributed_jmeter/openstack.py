import time
import datetime

import novaclient.v2 as novaclient
import requests
import json

from cloudscale.distributed_jmeter.aws import AWS


class OpenStack(AWS):

    def __init__(self, r_path, scenario_path, output_directory, cfg, logger):
        super(OpenStack, self).__init__(cfg, scenario_path, r_path, output_directory, logger)

    def init(self):
        self.host = self.cfg.get('OPENSTACK', 'host')
        self.startup_threads = self.cfg.get('TEST', 'startup_threads')
        self.rest_threads = self.cfg.get('TEST', 'rest_threads')
        self.host = self.cfg.get('SHOWCASE', 'host')
        self.num_jmeter_slaves = int(self.cfg.get('TEST', 'num_jmeter_slaves'))
        self.key_pair = self.cfg.get('OPENSTACK', 'key_pair_path')
        self.key_name = self.cfg.get('OPENSTACK', 'key_name')
        self.jmeter_url = self.cfg.get('SCENARIO', 'jmeter_url')
        self.user = self.cfg.get('OPENSTACK', 'remote_user')
        self.ips = self.cfg.get('SCENARIO', 'instance_names')
        self.image = self.cfg.get('OPENSTACK', 'image')
        self.flavor = self.cfg.get('OPENSTACK', 'instance_type')
        self.frontend_instances_identifier = None
        self.rds_identifiers = None
        self.is_autoscalable = False
        self.scenario_duration = self.cfg.get('SCENARIO', 'duration_in_minutes')
        self.num_threads = int(self.cfg.get('SCENARIO', 'num_threads'))
        self.nc = novaclient.Client(
            self.cfg.get('OPENSTACK', 'user'),
            self.cfg.get('OPENSTACK', 'pwd'),
            self.cfg.get('OPENSTACK', 'tenant'),
            auth_url=self.cfg.get('OPENSTACK', 'url')
        )

    def start(self):
        if self.ips != "":
            self.server_ids = [self.nc.servers.find(name=x).id for x in self.ips.split(",")]
        else:
            self.server_ids = [self.create_instance('jmeter-%s' % i) for i in range(self.num_jmeter_slaves) ]

        ips = []
        for server_id in self.server_ids:
            time.sleep(30)
            ip = self.add_floating_ip(server_id)
            ips.append(ip)

        time.sleep(60)
        for ip in ips:
            super(OpenStack, self).setup_master(ip)

        super(OpenStack, self).run_masters(ips)

    def create_instance(self, name):
        self.logger.log("Creating JMeter instance %s" % name)

        image = self.get_image(self.image)
        flavor = self.get_flavor(self.flavor)

        try:
            server = self.nc.servers.create(name,  image, flavor, key_name=self.key_name)
            time.sleep(10)
            self.wait_active(server.id)
        except Exception as e:
            raise e


        for server in self.nc.servers.list():
            if server._info['name'] == name:
                return server.id

    def wait_active(self, server_id):
        self.logger.log("Waiting for instance to be built . . .")
        status = self.wait_for_instance_status(server_id, u'BUILD', u'ACTIVE')
        if not status:
            self.logger.log("Can not start instance %s!" % server_id)
            return False
        return True

    def wait_for_instance_status(self, server_id, current_status, wait_for_status):
        while True:
            server = self.nc.servers.get(server_id)
            if server.status != current_status:
                if server.status == wait_for_status:
                    return True
                return False
            time.sleep(10)

    def get_image(self, name):
        for image in self.nc.images.list():
            if image.name == name:
                return image

    def get_flavor(self, name):
        for flavor in self.nc.flavors.list():
            if flavor.name == name:
                return flavor

    def add_floating_ip(self, server_id):

        server = self.nc.servers.get(server_id)
        # tenant = self.cfg.get('OPENSTACK', 'tenant')
        # if len(server._info['addresses'][tenant]) > 1:
        #     return server._info['addresses'][tenant][1]['addr']

        unallocated_floating_ips = self.nc.floating_ips.findall(fixed_ip=None)
        if len(unallocated_floating_ips) < 1:
            unallocated_floating_ips.append(self.nc.floating_ips.create())

        i=0
        floating_ip = unallocated_floating_ips[i]
        i+=1
        while floating_ip.ip == '10.10.43.74' and i < len(unallocated_floating_ips):
            floating_ip = unallocated_floating_ips[i]
        server.add_floating_ip(floating_ip)
        return floating_ip.ip

    def get_instances_by_tag(self, tag, value):
        return []

    def terminate_instances(self, ips):
        #for server_id in self.server_ids:
        #    for server in self.nc.servers.list():
        #        if server.id == server_id:
        #            server.delete()
        return

    def get_cloudwatch_ec2_data(self, start_time, end_time, instance_ids):
        r = requests.get('http://10.10.43.51/ganglia/graph.php?r=hour&title=cloudscale&vl=&x=&n=&hreg[]=cloudscale-sc&mreg[]=cpu_user&gtype=line&glegend=show&aggregate=1&embed=1&_=1446550633887&json=1')
        response_data = []
        if r.status_code == 200:
            data = json.loads(r.content)
            for instance in data:
                instance_name = instance['metric_name']
                response_data.append({
                            'instance_id': instance_name,
                            'data': self._get_datapoints(instance['datapoints'], start_time, end_time)
                        })
        return response_data

    def _get_datapoints(self, datapoints, start_time, end_time):
        try:
            data_cpu = []
            duration = int((end_time - start_time).total_seconds()/60)
            per_minutes = [[] for _ in xrange(duration+1)]
            for d in datapoints:
                timestamp = datetime.datetime.utcfromtimestamp(d[1])
                if timestamp >= start_time and timestamp <= end_time:
                    minute = int((timestamp - start_time).total_seconds()/60)
                    per_minutes[minute].append(d[0])

            i = 1
            for a in per_minutes:
                sum = 0
                for b in a:
                    sum += int(b)
                avg = sum/len(a)
                timestamp = datetime.datetime.fromtimestamp(0) + datetime.timedelta(minutes=i)

                data_cpu.append({'Timestamp': timestamp, 'Average': avg})
                i+=1

            return data_cpu
        except Exception as e:
            raise e

    def get_cloudwatch_rds_data(self, start_time, end_time, instance_ids):
        r = requests.get('http://10.10.43.51/ganglia/graph.php?r=hour&title=cloudscale&vl=&x=&n=&hreg[]=cloudscale-db&mreg[]=cpu_user&gtype=line&glegend=show&aggregate=1&embed=1&_=1446550633887&json=1')
        response_data = []
        if r.status_code == 200:
            data = json.loads(r.content)
            for instance in data:
                instance_name = instance['metric_name']
                response_data.append({
                            'instance_id': instance_name,
                            'data': self._get_datapoints(instance['datapoints'], start_time, end_time)
                        })
        return response_data