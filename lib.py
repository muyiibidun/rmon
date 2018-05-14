from __future__ import print_function
import multiprocessing, time, datetime, sys, csv, os
import ConfigParser, subprocess, psutil
import tarfile, glob

class IProcess:
    def run(self):
        pass

class ProcessWrapper(multiprocessing.Process):
    def __init__(self, task):
        multiprocessing.Process.__init__(self, name=task.pname)
        self.task = task

    def run(self):
        self.task.set_pid(multiprocessing.current_process().pid)
        sys.stdout.flush()
        print("%s(%d) is started @%d" % (self.task.pname, self.task.pid, round(time.time())))

        if isinstance(self.task, IProcess):
            self.task.run()

        print("%s(%d) is exited @%d" % (self.task.pname, self.task.pid, round(time.time())))
        sys.stdout.flush()

class Funcs:
    @staticmethod
    def get_configs(config_file):
        if os.path.exists(config_file):
            try:
                config = ConfigParser.ConfigParser()
                config.read(config_file)
                sections = config.sections()
                config_sections = {}  # dictionary of all sections
                for section in sections:
                    entries = config.options(section)
                    dic = {}  # dictionary of each section
                    for entry in entries:
                        dic[entry] = config.get(section, entry)
                    config_sections[section] = dic
            except IOError as err:
                print("Error reading config file.\n%s " % err)
                sys.exit()
        else:
            print("File '%s' does not exist." % config_file)
            sys.exit()
        return config_sections

    @staticmethod
    def get_timestamp():
        nw = datetime.datetime.now().timetuple()
        stamp = "{0}{1:02d}{2:02d}{3:02d}{4:02d}".format(str(nw.tm_year)[-2:], nw.tm_mon, nw.tm_mday, nw.tm_hour, nw.tm_min)

        return stamp

    @staticmethod
    def add_timestamp(msg):
        #appends unix epoch timestamp
        timestamp = str(int(round(time.time())))
        msg = timestamp + "," + msg
        return msg

    @staticmethod
    def maketar(tar_name="", glob_pattern="", extra=None):
        tar = tarfile.open(tar_name, "w:tar")
        for file in glob.glob(glob_pattern):
            tar.add(file)
        if extra:
            for item in extra:
                tar.add(item)
        tar.close()
        return

    @staticmethod
    def run_local_command(commands=None, stdout=os.devnull):
        # synchronous: waits till end of command
        # subprocess.call(self.CMDs, stdout=subprocess.PIPE)
        # asynchronous: returns immediately,
        proc = subprocess.Popen(commands, shell=False, stdout=open(stdout, 'w'), stderr=subprocess.STDOUT)
        return

class LogMode:
    STDOUT = 1
    FILE = 2
    DB = 3

class Collector(IProcess):
    def __init__(self, subsystems=None, duration=None, sampling_interval=1,
                 mode=LogMode.STDOUT, disk_info=None,log_dest="",log_desc="", email=""):
        self.pname = self.__class__.__name__
        self.pid = 0
        self.duration = duration
        self.interval = sampling_interval
        self.logmode = mode
        self.header = PSUTILHelper.extract_log_headers(subsystems)
        self.subsystems = subsystems
        self.disk_info = disk_info
        self.email = email

        if self.logmode == LogMode.FILE:
            FileHandler.init_log(log_desc=log_desc, header=self.header, dpath=log_dest)

    def run(self):
        # runs till end of schedule time
        start = time.time()
        end = start + self.duration
        next_sampling_time = start
        first_interval = True

        while time.time() <= end:
            # is it sampling time?
            if time.time() >= next_sampling_time:
                timestamp = int(round(time.time()))
                # get a list of measurements
                sysstats = PSUTILHelper.get_sysstats(subsystems=self.subsystems, xtra_args=self.disk_info)

                #prepend the timestamp to the measurements
                msg = str(timestamp) + "," + ",".join(map(str,sysstats))

                if self.logmode == LogMode.STDOUT:
                    if first_interval:
                        print("%s(%d): %s" % (self.pname, self.pid, self.header))
                        first_interval = False
                    # send to console
                    print("%s(%d): %s" % (self.pname, self.pid, msg))
                elif self.logmode == LogMode.FILE:
                    if first_interval:
                        print("%s(%d): %s" % (self.pname, self.pid, self.header))
                        first_interval = False
                    print("%s(%d): %s" % (self.pname, self.pid, msg))
                    # write to log file
                    FileHandler.write_row(msg.split(','))

                # compute new sampling time
                next_sampling_time = time.time() + self.interval
            # otherwise
            time.sleep(self.interval)
        return

    def set_pid(self, pid):
        self.pid = pid

    def send_log(self, email_addr="me@domain.com"):
        FileHandler.log2mail(addr=email_addr)

class PSUTILHelper:
    Fields = {
    "cpu":{
            "cpu":["user", "nice", "system", "idle", "iowait", "irq", "softirq", "steal", "guest", "guest_nice"],
            "cpu_sys":["ctx_switches", "interrupts", "soft_interrupts", "syscalls"]
           },
    "mem":{"virtual":["total", "available", "percent", "used", "free", "active", "inactive", "buffers", "cached", "shared"]},
    "disk":{
            "io":["read_count", "write_count", "read_bytes", "write_bytes", "read_time", "write_time"],
            "usage":["total", "used", "free", "percent"]
           },
    "net": {"io":["bytes_sent", "bytes_recv", "packets_sent", "packets_recv", "errin", "errout", "dropin", "dropout"]}
    }
    # hack: due to dict storing things out of order
    #FieldsCache = {"cpu":["cpu", "cpu_sys"], "mem":["virtual"],"disk":["io","usage"],"net":["io"]}
    SubsysToMethod = {"cpu":[("cpu","cpu_times_percent"), ("cpu_sys","cpu_stats")],
                       "mem":[("virtual","virtual_memory")],
                       "disk":[("io","disk_io_counters"),("usage","disk_usage")],
                       "net":[("io","net_io_counters")]}

    @staticmethod
    def extract_log_headers(subsystems=None, field0="timestamp"):
        header = [field0]
        for key in subsystems:
            for subkey, _ in PSUTILHelper.SubsysToMethod[key]:
                for field in PSUTILHelper.Fields[key][subkey]:
                    header.append(key +"_"+field)
        return header

    @staticmethod
    def get_sysstats(subsystems="", xtra_args=None):
        measurements = []
        for subsys in subsystems:
            subsys_stats = PSUTILHelper.get_subsys_stats(subsys=subsys, xtra_args=xtra_args)
            measurements.extend(subsys_stats)
        return measurements

    @staticmethod
    def get_subsys_stats(subsys=None, xtra_args=None):
        stats = []
        disk_name, disk_device = xtra_args[0],  xtra_args[1]

        for subkey, ps_method_str in PSUTILHelper.SubsysToMethod[subsys]:
            # dynamically bind method to the name
            ps_method = getattr(psutil, ps_method_str)
            if subsys == "disk":
                # disk stat method need to know partition of interest
                if subkey == "io":
                    stat_dict = ps_method(perdisk=True)[disk_name]._asdict()
                elif subkey == "usage":
                    stat_dict = ps_method(path=disk_device)._asdict()
            else:
                stat_dict = ps_method()._asdict()

            for field in PSUTILHelper.Fields[subsys][subkey]:
                stats.append(stat_dict[field])
        return stats

class FileHandler:
    logname = ""
    logstamp = ""
    logdir = ""

    @staticmethod
    def init_log(log_desc="log", header=None, logstamp=" ", dpath="logs"):
        FileHandler.logdir = dpath
        # assign formatted datetime to log
        FileHandler.logstamp = Funcs.get_timestamp() if logstamp == " " else logstamp
        # make fullpath name
        if FileHandler.logdir=="":
            FileHandler.logname = os.path.join(os.getcwd(), "{0}-{1}.csv".format(log_desc, FileHandler.logstamp))
        else:
            FileHandler.logname = os.path.join(os.getcwd(), FileHandler.logdir, "{0}-{1}.csv".format(log_desc, FileHandler.logstamp))
        # if header is provided
        if header:
            with open(FileHandler.logname, "wt") as _fhandle:
                writer = csv.writer(_fhandle)
                writer.writerow(tuple(header))
        else:
            with open(FileHandler.logname, "wt") as _fhandle:
                writer = csv.writer(_fhandle)
                writer.writerow(tuple([" ", " "]))

    @staticmethod
    def write_row(row=None):
        with open(FileHandler.logname, "at") as _fhandle:
            writer = csv.writer(_fhandle)
            writer.writerow(tuple(row))

    @staticmethod
    def log2mail(addr=None):
        if addr: #and os.path.exists(FileHandler.logname):
            # create tar ball from logs
            tar_ = "./%s/explog-%s.tar" % (FileHandler.logdir, FileHandler.logstamp)
            glob_ = "./%s/*-%s*.*" % (FileHandler.logdir, FileHandler.logstamp)
            Funcs.maketar(tar_name=tar_, glob_pattern=glob_)
            # send email with MPACK tool
            cmd = ["mpack", "-s", '"Logs for run: %s"' % FileHandler.logstamp, tar_, addr]
            Funcs.run_local_command(commands=cmd)
