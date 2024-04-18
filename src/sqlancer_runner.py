import subprocess
import os

from survivor_mutant import survivor_mutants

def differential_test(sql_file, file_to_test, mutation_id, res_track, err_track, ret_track, print_diff=False):
    if os.path.exists("temp_ref.db"):
        os.remove("temp_ref.db")
    if os.path.exists("temp_mut.db"):
        os.remove("temp_mut.db")

    different = False
    diff_line = -1

    my_env = os.environ.copy()
    p_ref = subprocess.Popen([f'sqlite3_dredd/sqlite3_{file_to_test}_mutations', "temp_ref.db"],
        stdin=subprocess.PIPE, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        env = my_env,
    )

    my_env["DREDD_ENABLED_MUTATION"] = str(mutation_id)
    p_mut = subprocess.Popen([f'sqlite3_dredd/sqlite3_{file_to_test}_mutations', "temp_mut.db"],
        stdin=subprocess.PIPE, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        env = my_env,
    )

    with open(sql_file, "rb") as f:
        s = f.read()
        while s[-1] != 59:  # ASCII FOR ';'
            s = s[:-1]
        res_ref, err_ref = p_ref.communicate(s)
        res_mut, err_mut = p_mut.communicate(s)

    os.remove("temp_ref.db")
    os.remove("temp_mut.db")

    if res_ref != res_track or err_ref != err_track or p_ref.returncode != ret_track:
        print(">>>>", res_ref != res_track, err_ref != err_track, p_ref.returncode != ret_track)
        print()
        return False

    return res_ref != res_mut or err_ref != err_mut or p_ref.returncode != p_mut.returncode

print('Finding survivor mutants of each files:')
# files = ['alter', 'analyze', 'attach', 'auth', 'backup', 'bitvec', 'btmutex', 'btree', 'build', 'callback', 'complete', 'ctime', 'date', 'dbpage', 'dbstat', 'delete', 'expr']
files = ['analyze', 'attach', 'auth', 'backup', 'bitvec', 'btmutex', 'btree', 'build', 'callback', 'complete', 'ctime', 'date', 'dbpage', 'dbstat', 'delete', 'expr']

survivors = dict()
for f in files:
    survivors[f] = set([m for m in survivor_mutants(f, True)])
print()


def kill_survivor(file, survivors, generation_count=1):
    sqlancer_killed = set()

    for _ in range(generation_count):
        # run sqlancer
        try:
            # p = os.getcwd()
            subprocess.run(['mkdir', '-p', f'sqlancer_temp_{file}'])
            subprocess.run([
                    'java',
                    '-jar',
                    '/home/jjf120/dredd_exp/sqlancer/target/sqlancer-2.0.0.jar',
                    '--num-queries',
                    '1000',
                    '--max-generated-databases',
                    '1',
                    'sqlite3',
                    '--oracle',
                    'FUZZER'
                ],
                cwd=f'sqlancer_temp_{file}'
            )
            # os.cwd(p)
        except Exception as err:
            print(err)

        for db in range(100):
            # run coverage
            if os.path.exists(f"temp_track_{file}.db"):
                os.remove(f"temp_track_{file}.db")
            
            my_env = os.environ.copy()
            my_env["DREDD_MUTANT_TRACKING_FILE"] = f"/home/jjf120/dredd_exp/temp_coverage_{file}_{db}.txt"
            p_track = subprocess.Popen(
                [f'sqlite3_dredd/sqlite3_{file}_tracking', f"temp_track_{file}_{db}.db"],
                stdin=subprocess.PIPE, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                env = my_env,
            )

            with open(f'sqlancer_temp_{file}/logs/sqlite3/database{db}-cur.log', "rb") as f:
                s = f.read()
                while s[-1] != 59:  # ASCII FOR ';'
                    s = s[:-1]
                res_track, err_track = p_track.communicate(s)

            os.remove(f"temp_track_{file}_{db}.db")

            with open(f"/home/jjf120/dredd_exp/temp_coverage_{file}_{db}.txt") as f:
                mutants_in_coverage = list(set([int(line.rstrip()) for line in f]))
            subprocess.run(['rm', f"/home/jjf120/dredd_exp/temp_coverage_{file}_{db}.txt"])

            for m, mutant in enumerate(mutants_in_coverage):
                if mutant not in survivors[file]:
                    continue

                # run differential
                if differential_test(
                        f'sqlancer_temp_{file}/logs/sqlite3/database{db}-cur.log',
                        file,
                        mutant,
                        res_track, 
                        err_track,
                        p_track.returncode,
                        print_diff=False,
                    ):
                    sqlancer_killed.add(mutant)
                    survivors[file].remove(mutant)
                    subprocess.run(['cp', f'sqlancer_temp_{file}/logs/sqlite3/database{db}-cur.log', f'sqlancer_runner_res/{file}_{mutant}.db'])

                print(f"Gen: {db}, Killed/Remain: {len(sqlancer_killed)}/{len(survivors[file])}, Testing: {m}/{len(mutants_in_coverage)}", end="\r")
                    
        subprocess.run(['rm', '-r', f'sqlancer_temp_{file}'])

            

kill_survivor('alter', survivors)



# print(all_survivors)


# def kill_mutants(mutants):
#     for m in mutants:
#         for i in range(100):
#             print(f"Mutant {m}: Testing database {i}", end="\r")
#             killed = differential_test(f"/home/jjf120/sqlancer/target/logs/sqlite3/database{i}-cur.log", m, True)
#             if killed:
#                 print(f"Mutant {m}: Killed on database {i}")
#                 break

# alter_servivor = [68,69,70,71,75,76,77,78,80,82,86,100,102,108,110,114,118,142,143,174,175,212,244,285,317,320,335,447,448,478,479,480,510,511,588,620,709,715,724,731,732,735,741,747,756,763,764,767,802,899,902,934,935,968,978,979,982,1000,1010,1011,1014,1040,1041,1044,1072,1073,1076,1088,1090,1091,1092,1093,1094,1095,1097,1098,1104,1136,1191,1234,1266,1280,1312,1372,1404,1413,1414,1415,1416,1417,1418,1445,1446,1447,1448,1449,1450,1478,1510,1516,1521,1523,1630,1631,1662,1663,1751,1759,1783,1791,1797,1798,1813,1816,1818,1829,1830,1845,1848,1850,1874,1881,1883,1906,1913,1915,1922,1923,1924,1925,1926,1927,1954,1955,1956,1957,1958,1959,1988,1989,1992,2000,2001,2002,2003,2004,2006,2007,2008,2020,2021,2024,2032,2033,2034,2035,2036,2038,2039,2040,2048,2049,2050,2051,2052,2053,2054,2056,2057,2058,2059,2060,2061,2062,2063,2068,2069,2072,2073,2080,2082,2083,2085,2086,2090,2091,2092,2094,2095,2100,2101,2104,2105,2114,2115,2116,2117,2118,2119,2120,2122,2131,2132,2133,2134,2135,2136,2137,2147,2148,2149,2150,2151,2152,2154,2163,2164,2165,2166,2167,2168,2169,2176,2177,2179,2180,2181,2182,2183,2184,2186,2187,2189,2190,2192,2193,2194,2195,2196,2197,2198,2199,2200,2201,2202,2208,2209,2211,2212,2213,2214,2215,2216,2218,2219,2221,2222,2224,2225,2226,2227,2228,2229,2230,2231,2232,2233,2234,2245,2246,2247,2248,2249,2252,2260,2269,2277,2278,2279,2280,2281,2284,2292,2301,2304,2311,2313,2315,2322,2336,2343,2345,2347,2354,2373,2374,2375,2376,2377,2380,2389,2390,2391,2392,2393,2394,2395,2405,2406,2407,2408,2409,2410,2412,2421,2422,2423,2424,2425,2426,2427,2437,2438,2442,2469,2470,2497,2574,2576,2584,2606,2608,2616,2651,2683,2700,2732,2759,2769,2770,2771,2772,2773,2774,2791,2801,2802,2803,2804,2805,2806,2819,2833,2836,2837,2838,2839,2840,2841,2851,2865,2868,2873,2890,2894,2901,2922,2926,2933,2951,2953,2954,2956,2957,2963,2964,2967,2968,2969,2970,2971,2972,2973,2974,2983,2985,2986,2988,2989,2995,2996,2999,3000,3001,3002,3003,3004,3005,3006,3007,3008,3009,3010,3011,3012,3013,3014,3015,3022,3054,3059,3060,3061,3403,3404,3435,3436,3591,3592,3595,3623,3624,3627,3696,3698,3699,3700,3701,3702,3725,3726,3735,3736,3737,3738,3739,3740,3757,3758,3767,3768,3769,3770,3771,3772,3779,3790,3801,3811,3822,3833,3845,3852,3858,3861,3865,3877,3884,3890,3893,3897,3914,3917,3918,3926,3927,3930,3931,3932,3933,3946,3949,3950,3958,3964,3965,3966,3967,3971,3972,3975,3976,3978,3979,3992,4007,4011,4024,4030,4033,4034,4056,4065,4066,4088,4109,4112,4113,4118,4119,4122,4123,4125,4141,4144,4150,4151,4154,4155,4157,4162,4163,4166,4178,4184,4191,4194,4195,4198,4210,4216,4223,4227,4236,4240,4244,4248,4252,4253,4259,4268,4272,4276,4280,4284,4285,4288,4289,4300,4306,4310,4313,4316,4317,4318,4319,4320,4321,4332,4338,4342,4345,4348,4349,4350,4351,4370,4371,4372,4373,4374,4375,4377,4378,4380,4381,4383,4384,4385,4404,4409,4410,4412,4413,4415,4419,4420,4421,4422,4423,4424,4451,4452,4453,4454,4455,4456,4630,4662,4738,4744,4748,4749,4750,4754,4756,4757,4762,4763,4770,4776,4780,4781,4782,4786,4788,4789,4794,4795,4817,4818,4849,4850,4883,4884,4915,4916,4928,4930,4932,4942,4943,4944,4960,4962,4964,4974,4975,4976,5074,5076,5106,5108,5130,5162,5186,5196,5202,5204,5205,5211,5212,5218,5228,5234,5236,5237,5243,5244,5248,5249,5251,5252,5255,5256,5257,5258,5259,5260,5261,5262,5263,5264,5265,5266,5267,5268,5269,5270,5271,5272,5273,5274,5292,5298,5302,5340,5364,5365,5366,5367,5368,5369,5372,5383,5384,5385,5386,5387,5388,5415,5416,5417,5418,5419,5420,5505,5537,5590,5592,5622,5624,5633,5653,5654,5685,5686,5834,5844,5866,5876,5960,5971,5976,5977,5979,5992,6003,6008,6009,6011,6024,6044,6049,6078,6088,6089,6094,6120,6121,6126,6152,6184,6209,6211,6212,6215,6216,6217,6218,6219,6231,6234,6241,6243,6244,6249,6250,6263,6266,6275,6276,6277,6278,6279,6280,6297,6307,6308,6309,6310,6311,6312,6329,6339,6340,6347,6348,6353,6356,6371,6372,6379,6380,6385,6388,6400,6401,6402,6403,6404,6405,6408,6409,6410,6415,6417,6418,6424,6425,6426,6430,6432,6433,6434,6435,6436,6437,6440,6441,6442,6447,6448,6449,6450,6451,6452,6453,6454,6455,6456,6457,6458,6462,6543,6552,6575,6584,6607,6612,6619,6620,6623,6644,6651,6652,6655,6676,6708,6714,6718,6721,6722,6724,6725,6736,6740,6741,6754,6768,6772,6773,6863,6891,6895,6913,6915,6927,6928,6933,6934,6935,6945,6947,6959,6960,6965,6966,6967,6984,6985,7016,7017,7180,7212,7370,7437,7451,7452,7469,7483,7484,7563,7595,7637,7638,7642,7643,7669,7670,7674,7675,7680,7683,7690,7698,7701,7712,7715,7722,7730,7733,7875,7884,7885,7886,7887,7888,7889,7907,7916,7917,7918,7919,7920,7921,8256,8258,8259,8262,8263,8264,8265,8266,8267,8268,8269,8270,8271,8272,8273,8274,8275,8276,8277,8278,8279,8280,8281,8282,8283,8284,8285,8286,8287,8288,8289,8290,8291,8292,8293,8294,8295,8296,8297,8298,8299,8300,8301,8302,8303,8304,8305,8306,8307,8308,8309,8310,8345,8377,8404,8436]
# differential_test2(f"/home/jjf120/sqlancer/target/logs/sqlite3/database{15}-cur.log", 70, True)
# alter_servivor = [447]
# kill_mutants(alter_servivor)