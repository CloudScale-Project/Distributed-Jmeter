#
#  Copyright (c) 2015 XLAB d.o.o.
#  All rights reserved. This program and the accompanying materials
#  are made available under the terms of the Eclipse Public License v1.0
#  which accompanies this distribution, and is available at
#  http://www.eclipse.org/legal/epl-v10.html
#
import sys
from cloudscale.distributed_jmeter.scripts.visualization.SLO import SLO
from cloudscale.distributed_jmeter.scripts.visualization.converters import Converters
from visualization.web_interactions import WebInteractions

max_time = SLO


def is_deviation_ok(dist, allowed_deviation, k):
    web_interactions = WebInteractions()
    if dist <= (web_interactions.get_probability(k) + allowed_deviation) and dist >= (web_interactions.get_probability(k) - allowed_deviation):
        return "yes"
    return"no"

def get_actual_deviation(dist, k):
    web_interactions = WebInteractions()
    actual_deviation = dist-web_interactions.get_probability(k)

    r = "< %.3f" % abs(actual_deviation)
    if float(actual_deviation) > 0:
        r = "> %.3f" % actual_deviation

    return r

def check(file_path):
    output = ""
    urls = {}
    unsuccessfull = 0
    all_requests = 0
    fp = open(file_path)
    for line in fp:
        converters = Converters()
        try:

            timestamp, estimated_time, operation, response_code, _, _, _  = line.split(",")
            url = converters.url_converter(operation)

            if url != None and max_time.has_key(url):
                all_requests+=1
                if not urls.has_key(url):
                    urls[url] = {}
                    urls[url]['times'] = []

                urls[url]['times'].append([estimated_time, response_code])

                if response_code != "200":
                    unsuccessfull += 1
        except Exception as e:
            output += "Exception occured\n"
            output += e.message + "\n"
            pass

    dist_sum = 0
    web_interactions = WebInteractions()
    output += "%-40s %s %-20s %s %-20s %s %-25s %s %-20s %s %-20s %s %-20s %s %-20s %s %-20s\n" % ("operation", "|", "status", "|", "# all request", "|", "# successfull requests", "|", "% of successfull", "|", "% of operation", "|", "allowed deviation", "|", "actual deviation", "|", "deviation ok?")
    separator = "".join(["-" for _ in xrange(len(output))]) + "\n"
    output += separator

    cummulative_violations = 0
    cummulative_successful = 0
    cummulative_all = 0
    for k in urls:
        count_succ = 0
        all = len(urls[k]['times'])

        for time, response_code in urls[k]['times']:
            if int(time) <= max_time[k] and response_code == "200":
                count_succ += 1

        cummulative_successful += count_succ
        cummulative_all += all

        dist = (all*100.0)/all_requests
        dist_sum = dist_sum + dist
        allowed_deviation = 0.05*web_interactions.get_probability(k)

        status = "NOT OK"
        p = (count_succ*100)/all
        if count_succ >= (all * 90) / 100:
            status = "OK"
            # p = 0

        cummulative_violations += p
        actual_deviation = get_actual_deviation(dist, k)
        deviation_ok = is_deviation_ok(dist, allowed_deviation, k)

        output += "%-40s %s %-20s %s %-20s %s %-25s %s %-20s %s %-20s %s %-20.3f %s %-20s %s %-20s\n" % (k, "|", status, "|", all, "|", count_succ, "|", p, "|", "%.3f%% (%.3f%%)" % (dist, web_interactions.get_probability(k)), "|", allowed_deviation, "|", actual_deviation, "|", deviation_ok)


    fp.close()
    output += separator
    output += "# ALL REQUESTS = %s, # UNSUCCESSFULL REQUESTS = %s, PROB SUM = %s, # SLO VIOLATIONS = %s%%\n" % (all_requests, unsuccessfull, dist_sum, (((cummulative_all-cummulative_successful)*100)/cummulative_all))

    return output


if __name__ == "__main__":
    print check(sys.argv[1])

