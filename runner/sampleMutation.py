import subprocess, os, getopt, sys, time

TIMEOUT_CONSTANT = 10

def extractErrorCount(output):
    for line in iter(output.splitlines()):
        if "errors out of" in line:
            return line
    return ""

def getTestSet(testlist):
    res = []
    with open(testlist, "r") as f:
        for line in f:
            res.append(line.rstrip('\n'))
    return res


def runTests(coverage_binary, mutation_binary, testset, outputfile, killedfile):
    coverage_filepath = os.getcwd() + "/coverage.txt"
    my_env = os.environ.copy()
    my_env["DREDD_MUTANT_TRACKING_FILE"] = coverage_filepath
    outputfile.write(f"status, test_name, mutant_id, description\n")
    killed = set()

    for index, test in enumerate(testset):
        print("Running:", test, f"{index + 1}/{len(testset)}")
        subprocess.run(['touch', coverage_filepath])

        start = time.time()
        process = subprocess.run([coverage_binary, test], env=my_env, stdout=subprocess.DEVNULL)
        end = time.time()
        base_time = end - start
        print(f"Time: {base_time}s")

        mutants = set()
        with open(coverage_filepath) as f:
            mutants = set([int(line.rstrip()) for line in f])
        subprocess.run(['rm', coverage_filepath])

        print("Number of mutants in coverage", len(mutants))

        if len(mutants) == 0:
            print()
            continue        

        killCount = 0
        surviveCount = 0
        skipCount = 0
        totalCount = 0
        
        for mutant in mutants:

            if mutant in killed:
                skipCount += 1
                totalCount += 1
                print(f"Killed: {killCount}, Survived: {surviveCount}, Skipped: {skipCount}", end='\r' if len(mutants) != totalCount else '\n')
                continue
        
            my_env["DREDD_ENABLED_MUTATION"] = str(mutant)
            status = ""
            description = ""
            try:
                result = subprocess.run([mutation_binary, test], timeout=base_time * TIMEOUT_CONSTANT, env=my_env, capture_output=True, text=True, check=True)
            except Exception as e:
                killCount += 1
                totalCount += 1
                killed.add(mutant)
                status = "KILLED"
                description = ' '.join(str(e).split()[3:])
                killedfile.write(f"{mutant}\n")
            else:
                testResult = extractErrorCount(result.stdout)
                description = ' '.join(testResult.split()[:6])
                surviveCount += 1
                status = "SURVIVE"
                totalCount += 1
            
            outputfile.write(f"{status}, {test}, {mutant}, {description}\n")
            print(f"Killed: {killCount}, Survived: {surviveCount}, Skipped: {skipCount}", end='\r' if len(mutants) != totalCount else '\n')
            subprocess.run(['rm', '-rf', 'testdir'])

        print()


csvfile = ""
try:
    mutation = sys.argv[1]
    coverage = sys.argv[2]
    tests = sys.argv[3]
    opts, args = getopt.getopt(sys.argv[4:],"ho:k:")
except getopt.GetoptError:
    print ('sampleMutation.py mutation coverage tests -o <csvfile> -k <killedfile>')
    sys.exit(2)


for opt, arg in opts:
    if opt == '-h':
        print('sampleMutation.py mutation coverage tests -o <csvfile> -k <killedfile>')
        sys.exit()
    elif opt == '-o':
        csvfile = arg
    elif opt == '-k':
        killedfile = arg

f = open(csvfile, "w")
f2 = open(killedfile, "a")
test = getTestSet(tests)
runTests(coverage, mutation, test, f, f2)
f.close()
f2.close()