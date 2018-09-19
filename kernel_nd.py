import os
import argparse
import multiprocessing
import subprocess

kernel_lib_dir = '/localdisk/bkc/debug/intel_next/daily'
kernel_lib_file = os.path.join(kernel_lib_dir, 'org.txt')
prj_dir = os.path.join((os.getcwd()).split('/')[:-4])

def args_init():
    global args
    parser = argparse.ArgumentParser()
    parser.add_argument('kernel_start', help='specify the first kernel directory name in org.txt, ex. 2018-09-07')
    parser.add_argument('kernel_end', help='specify the last kernel directory name in org.txt, ex. 2018-09-07')
    parser.add_argument('--process-num', '-p', default='13', help='specify the maximum process that run parallel')
    args = parser.parse_args()

def get_kernel_list():
    tmp_list = os.listdir(kernel_lib_dir)
    for i in range(len(tmp_list)):
        if args.kernel_start in tmp_list[i]:
            spos = i
            break
    for i in range(len(tmp_list)):
        if args.kernel_end in tmp_list[i]:
            epos = i
    return [os.path.join(kernel_lib_dir, item) for item in
            (tmp_list[spos:epos + 1] if epos + 1 < len(tmp_list) else tmp_list[spos:])]

def get_diff_craff(local_linux_kernel):
    command = os.path.join(prj_dir, 'simics') + "-e \$local_linux_kernel=" + local_linux_kernel + ' -e \$semi_auto=TRUE ' \
              " " + os.path.join(prj_dir, 'dbg/triage/kernel/update_kernel.simics')
    quit_code = subprocess.call(command, shell=True)
    for item in os.listdir(prj_dir):
        if item[-6:] == '.craff' and item[-6:] in local_linux_kernel:
            return os.path.join(prj_dir, item)

def run_tc(tc_name, pos):
    toplog_dir = os.path.join(prj_dir, 'log', '00')
    if not os.path.exists(toplog_dir):
        os.makedirs(toplog_dir)
    command = os.path.join(prj_dir, 'simics') + \
              "-e \$toplog_dir=" + toplog_dir + \
              "-e \$semi_auto=TRUE " + tc_name
    quit_code = subprocess.call(command, shell=True)
    return (pos, True) if quit_code == 11 else (pos, False)

def mycmp(x, y):
    return x[0] < y[0]

if __name__ == '__main__':
    args_init()
    kernel_list = get_kernel_list()
    diff_craff_list = []

    res = []
    pool = multiprocessing.Pool(processes=args.process_num)
    for item in kernel_list:
        res.append(pool.apply_async(get_diff_craff, args=(item,)))
    pool.close()
    pool.join()

    diff_craff_list = [item.get() for item in res]
    diff_craff_list.sort()

    run_start = 0
    run_end = len(diff_craff_list)
    gap = (run_end - run_start) / args.process_num;
    while run_end > run_start:
        res = []
        pool = multiprocessing.Pool(processes=min(args.process_num, run_end - run_start - 1))
        for item in diff_craff_list[run_start:run_end:gap]:
            res.append(pool.apply_async(run_tc, args=(args.tc_name, diff_craff_list.index(item))))
        pool.close()
        pool.join()
        tmp_list = [item.get() for item in res]
        tmp_list.sort(cmp=mycmp)
        for i in range(len(tmp_list)):
            if tmp_list[i][1] == True and run_start <= tmp_list[i][0]:
                run_start = tmp_list[i][0] + 1
        for i in range(len(tmp_list)):
            if tmp_list[i][1] == False and run_end > tmp_list[i][0]:
                run_end = tmp_list[i][0]

    if run_end == len(diff_craff_list):
        print "all pass"
    else:
        print "fail at " + diff_craff_list[run_end]
