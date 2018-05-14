from __future__ import print_function
import multiprocessing, sys, time
from optparse import OptionParser
from lib import ProcessWrapper, Collector, Funcs


def run(cmd_options, pid):
    configs = Funcs.get_configs(cmd_options.configFile)
    confs = configs["general"]
    # For test run
    duration = float(cmd_options.duration)
    interval = int(cmd_options.interval)
    logmode = int(cmd_options.logmode)
    duration += interval # pad up the timeout so samples can be complete;
    disk0_ = (confs["disks"].split(",")[0]).split(":")
    disk0_info = disk0_[0], disk0_[1]

    # create Collector process
    collector = Collector(subsystems=str(confs["subsystems"]).split(","), duration=duration,
                          sampling_interval=interval, mode=logmode, disk_info=disk0_info,
                          log_dest=confs["log_destination"],log_desc="rmon")

    collector_proc = ProcessWrapper(collector)

    # run all processes
    collector_proc.start()
    collector_proc.join()

    if cmd_options.sendmail:
        email = cmd_options.sendmail
        collector.send_log(email_addr=str(email))
        print("RMon(%d): Archive mailed to %s." % (pid, email))
    return


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option('-c', '--config', dest='configFile', help='Path to CONFIGFILE', metavar='CONFIGFILE')
    parser.add_option('-i', '--interval', dest='interval', help='Sampling INTERVAL in secs. Default=20',
                      metavar='INTERVAL', default=20)
    parser.add_option('-d', '--duration', dest='duration', help='Estimated DURATION of run in secs. Default=300',
                      metavar='DURATION', default=300)
    parser.add_option('-l', '--logmode', dest='logmode', help='Select (1): STDOUT, (2): File, or (3): DB LOGMODE Default=1',
                      metavar='LOGMODE', default=1)
    parser.add_option('-s', '--sendmail', dest='sendmail', help='Sends compressed log to provided EMAIL Default=NONE',
                      metavar='SENDMAIL', default=None)

    (options, args) = parser.parse_args()

    if options.configFile:
        print("==============================================================")
        pid = multiprocessing.current_process().pid
        t0 = time.time()
        print("RMon(%d): Started @%.0f" % (pid, t0))
        run(options, pid)
        # exit
        print("RMon(%d): Run completed @%.0f \nTime elapsed: %.0f seconds" % (pid, time.time(), time.time()-t0))
        print("==============================================================")
    else:
        print('Syntax: Type python rmon.py [-h] | [--help] for help.')
        sys.exit()
