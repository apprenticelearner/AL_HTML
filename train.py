# Used to start training an Apprentice Learner agent interactively or via example/model tracing. 
# 

import argparse,sys,os, atexit
import subprocess, threading
from subprocess import check_output
import socket, errno
import signal, time
from datetime import datetime

al_process = None
ctat_process = None
al_thread = None
ctat_thread = None
calling_dir = None
CONFIG_DEFAULT = "net.conf"


def read_conf(ns, path):
    # args = {}

    with open(path,'r') as f:
        for line in f:
            x = line.split("=")
            if(len(x) > 1 and getattr(ns,x[0],None) == None):
                key = x[0].lower();
                val = x[1].strip('\"\'\n \t\f\r');
                if("port" in key): 
                    try:
                        val  = int(val)
                    except ValueError as e:
                        print("Invalid port %s for %s." % (val,key), file=sys.stderr)
                        sys.exit()

                setattr(ns, key, val); #Strip quotes and whitespace
    return ns


def force_kill_port(port):
    print("Attempting force kill...")

    if("linux" in sys.platform):
        try:
            tokill =  [int(x) for x in check_output(["lsof", "-Pi", ":" + str(port), "-sTCP:LISTEN", "-t"]).splitlines()]
            print("Found processes: %s bound to %s" % (tokill, port))
        except Exception as e:
            #At this point nothing popped up so we're good
            return True;
    else:
        raise Warning("Force kill (-f/--force) not implemented for operating system %r" % sys.platform)
        return False;
    print("Killing processes: %s" % tokill)
    for pid in tokill:
        kill_group(pid)
    return True
    # os.kill(pid, signal.SIGTERM)


def check_port(host, port, force=False):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        s.bind((host, port))
    except socket.error as e:
        if(force):
            
            return force_kill_port(port)
            # time.sleep(.1)
            # return check_port(host,port,False)
        else:
            print(e)
        return False
    try:
        s.shutdown(socket.SHUT_RDWR)
    except:
        pass
    s.close()
    return True

def port_error(nm, port):
    raise socket.error( "Failed to start %s at port %s. Port already in use." %(nm,port) )
    sys.exit()

def waitAndExit(proc, onExit):

    proc.wait()
    onExit()

def kill_group(p):
    if(isinstance(p,int)):
        pgid = os.getpgid(p)
    else:
        pgid = os.getpgid(p.pid)
    print("PGID", pgid)
    os.killpg(pgid, signal.SIGTERM) 

def kill_all():
    global al_process,ctat_process
    print("KILL ALL", al_process.pid,ctat_process)
    # al_process.stderr = None
    # ctat_process.stderr = None
    # al_process.stdout = None
    # ctat_process.stdout = None
    # al_process.stderr.close()
    # ctat_process.stderr.close()
    # temp_stderr = sys.stderr
    # sys.stderr = None 
    # sys.stdout = None 
    os.killpg(os.getpgid(), signal.SIGTERM) 
    # sys.stderr = temp_stderr
    # if(al_process != None): kill_group(al_process)
    # if(ctat_process != None): kill_group(ctat_process)
    # if(al_process != None): al_process.terminate()
    # if(ctat_process != None): ctat_process.terminate()


def apply_wd(path):
    path = os.path.expandvars(path)
    if(not os.path.isabs(path)):
        path = os.path.join(calling_dir,path)
    return path


def parse_args(argv):
    parser = argparse.ArgumentParser(description='Convert ROOT data to numpy arrays stored as HDF5 for Machine Learning use.')
    parser.add_argument('training', type=str, metavar="<training_file>.json",
        help="A JSON file that specifies the sequence of problems to train on.")
    parser.add_argument('-f', '--force', action='store_true',default=False, dest = "force",
        help="Force kill processes that hold up ports we want to use. Only implemented for Linux systems.")
    parser.add_argument('-i', '--interactive', action='store_true',default=False, dest = "interactive",
        help="Indicates that AL should trained interactively by the user instead of automatically by example/model tracing.")

    parser.add_argument('-a', '--al-port' , default=None, dest = "al_port",     metavar="<AL_port>",
        type=int, help="The port for the apprentice learner server.")
    parser.add_argument('-c', '--ctat-port',default=None, dest = "ctat_port",   metavar="<CTAT_port>",
        type=int, help="The port where the ctat interface and logging server bind to.")

    parser.add_argument('--al-host' , default="localhost", dest = "al_host",     metavar="<AL_host>",
        help="The host url for the apprentice learner server. Default=localhost.")
    parser.add_argument('--ctat-host' , default="localhost", dest = "ctat_host",     metavar="<CTAT_host>",
        help="The host url for the apprentice learner server. Default=localhost.")

    parser.add_argument('-d', '--al-dir' ,  default=None, dest = "al_dir",      metavar="<AL_dir>",
        help="The directory where the apprentice learner API can be found.")
    parser.add_argument('-b', '--broswer' , default=None, dest = "browser",     metavar="<browser>",
        help="The browser executable to run CTAT on.")
    parser.add_argument('-l', '--log-dir' , default=None, dest = "log_dir",     metavar="<log_dir>",
        help="The directory where tab deliminated logging files are written. Overridden by -o/--output.")
    parser.add_argument('-o', '--output' ,  default=None, dest = "output",      metavar="<output>",
        help="The tab deliminated logging file for the session should go to. By default can be found in /log directory")
    parser.add_argument('--config' ,  default=CONFIG_DEFAULT, dest = "config",      metavar="<config>.conf",
        help="Bash style configuration file used for setting default variables. ")
    parser.add_argument('-w' , "--working-directory",  default=None, dest = "wd",      metavar="<working-directory>",
        help="The working directory of the ctat server. By default it is the directory where training.json is located")

    try:
        args = parser.parse_args(argv)
        # args.setattr(args, "training", args.training[0]) # dunno why it comes in a list
        
    except Exception:
        parser.print_usage()
        sys.exit()

    read_conf(args, args.config)


    args.log_dir = os.path.abspath(apply_wd(args.log_dir))
    args.al_dir = os.path.abspath(apply_wd(args.al_dir))
    # os.path.join(calling_dir,args.al_dir)
    args.training = os.path.os.path.relpath(apply_wd(args.training), start=os.getcwd())


    assert os.path.isfile(args.training), "No such file %r" % args.training
    assert args.al_port != None, "AL_PORT not specified or set in %s" % args.config
    assert args.ctat_port != None, "CTAT_PORT not specified or set in %s" % args.config 
    assert args.al_dir != None, "AL_DIR not specified or set in %s" % args.config
    assert args.browser != None, "BROWSER not specified or set in %s" % args.config 
    assert args.log_dir != None, "LOG_DIR not specified or set in %s" % args.config 

    if(args.output == None):
        args.output = "%s/%sLog-%s.txt" % (args.log_dir , os.path.basename(args.training).split(".")[0], datetime.now().strftime("%Y-%m-%d-%H:%M:%S"))

    
    args.output = os.path.abspath(apply_wd(args.output))


    return args

# RUN = True

# def stop(sig, frame):
#     print("SIGNAL CAUGHT", sig,al_process,ctat_process)
#     RUN =False
#     kill_all()

# signal.signal(signal.SIGTERM, stop )
# signal.signal(signal.SIGINT, stop)


def main(args):
    global al_process,ctat_process

    if(check_port(args.al_host, args.al_port, args.force)):
        # pass
        al_process =  subprocess.Popen([sys.executable, args.al_dir + "/manage.py", "runserver", str(args.al_host) + ":" + str(args.al_port)])
        # al_thread = threading.Thread(target=waitAndExit, args=(al_process, kill_all))
        # al_thread.start()
    else:
        port_error("AL", args.al_port)

    if(check_port(args.ctat_host, args.ctat_port, args.force)):
        pass
        ctat_process = subprocess.Popen([sys.executable, "src/host_server.py", str(args.ctat_port), args.output])
        # ctat_thread = threading.Thread(target=waitAndExit, args=(ctat_process, kill_all))
        # ctat_thread.start()
        
    else:
        port_error("CTAT", args.ctat_port)

    ctat_url = "http://localhost:%s/?training=%s&al_url=http://localhost:%s" %(args.ctat_port, args.training,args.al_port)
    if(args.wd != None): ctat_url += "&wd=" + args.wd

    browser_process = subprocess.Popen([args.browser, ctat_url])

    # al_process.wait()
    print("AL PROCESS")
    while True:
        if(al_process.poll() != None or ctat_process.poll() != None):
            break
        # try:
        time.sleep(.1)
            # ctat_process.wait(.1)
        # except:
            # pass

    # ctat_thread.join()

    kill_all()
    sys.exit()

if __name__ == "__main__":
    calling_dir = os.getcwd()

    #Always run this script from the directory where it lives
    abspath = os.path.abspath(__file__)
    print("ABSPATH", abspath)
    dname = os.path.dirname(abspath)
    os.chdir(dname)

    # atexit.register(kill_all);
    args = parse_args(sys.argv[1:])
    # print(args, type(args))
    main(args)