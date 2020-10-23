import simpy
import numpy as np
import random
import matplotlib.pyplot as plt

env = simpy.Environment()


scheduled_interarrivals = []
actual_interarrivals = []

my_delay = 300  # Giving the delay a constant, this varies as we would like
t_landing = 60
t_takeoff = 60
my_ta = 45*60
e_weather1 = 3600
e_weather2 = 7200
e_snow = 45*60
t_p = 60*10
t_i = 600
t_deicing = 600


runway = simpy.PriorityResource(env, capacity=2) # Implementing resources
dTruck = simpy.Resource(env, capacity=1)


def weather1():
    return random.choice(np.random.exponential(e_weather1, 1000))

def weather2():
    return random.choice(np.random.exponential(e_weather2, 1000))

def snow():
    return random.choice(np.random.exponential(e_snow, 1000))


def badWeather(env, priority):
    with runway.request(env, priority) as req:
        snowing = random.choice([True, False])
        if snowing:
            print("Started the system with snowy weather")
        while True:
            if snowing:
                t1 = env.now
                snowtime = weather1()
                while int(env.now - t1) < snowtime:
                    timeToFillRunways = snow()
                    if (env.now - t1) >= timeToFillRunways:
                        print("Snow on runways. Start plowing at: ", end="")
                        announceTime(env.now)
                        yield req
                        yield req
                        yield env.timeout(t_p)
                        yield runway.release(req)
                        print("Finished plowing first runway at: ", end="")
                        announceTime(env.now)
                        yield env.timeout(t_p)
                        yield runway.release(req)
                        print("Finished plowing second runway at: ", end="")
                        announceTime(env.now)
                        break
                    else:
                        yield env.timeout(10)
                    snowing = False
            else:
                un_snowtime = weather2()
                yield env.timeout(un_snowtime)
                print("Started snowing at: ", end="")
                announceTime(env.now)
                snowing = True

def arrival_intensity(seconds):
    # This is a function that describes Table 1 in the Lab
    # A dictionary could also be used, but I found the "brute force" way simplest at the moment
    t = (seconds / 3600) % 24  # Gives time in integer hours
    if t > 24:
        return 0
    elif 0< t < 5:
        return 0
    elif 5 < t <= 8:
        return 120
    elif 8 < t <= 11:
        return 30
    elif 11 < t <= 15:
        return 150
    elif 15 < t <= 20:
        return 30
    elif 20 < t <= 24:
        return 120
    else:
        return 0

def announceTime(time):
    day = int(time // (24 * 3600))
    time = time % (24 * 3600)
    hour = int(time // 3600)
    time %= 3600
    minutes = int(time // 60)
    time %= 60
    seconds = int(time)
    print("Day:", day, ",", "Time: ", hour, ":", minutes, ":", seconds)


def delay():
    x = random.randint(0, 1)
    if x == 0:
        return 0
    else:
        return random.choice(np.random.gamma(3, my_delay/3, 1000))

def turnaround():
    return random.choice(np.random.gamma(7,my_ta/7, 1))


def inter_arrival(t_guard, t):
    if 0 < ((t / 3600) % 24) < 5:
        return (5 * 3600) - (t % 86400)
    t1 = random.choice(np.random.exponential(arrival_intensity(t), 1000))
    if t_guard > t1:
        return t_guard
    else:
        return t1


def plane_generator(env, t_guard):
    id = 1

    while True:
        print("\n")

        t_interarrival = inter_arrival(t_guard, env.now)
        scheduled_interarrivals.append(
            t_interarrival)  # This simply adds the larger of the values T_guard and a random selected value from the distribution of intensities
        yield env.timeout(
            t_interarrival)  # We need to "hold" the plane for the larger of t_guard and expected interarrival

        delay1 = delay()  # To se if planes are previously delayed
        yield env.timeout(delay1)  # Holding the plane for the time it is delayed

        env.process(airPlane(env, id, 2))

        """if delay1 == 0:
            print("Plane number ", id, " arriving with no previous delay")
        else:
            print("Plane ", id,  " arriving with delay: ", int(delay1/3600),"hrs, ",int(delay1/60),"minutes")"""

        id += 1

def airPlane(env, id, priority):
    with runway.request(env, priority) as req:

        print("Plane", id, "Requesting runway for landing at: ", end="")
        announceTime(env.now)
        yield req
        yield env.timeout(t_landing)
        print(id, " landed successfully at ", end=" ")
        announceTime(env.now)
        actual_interarrivals.append(int((env.now/3600)%24))
        runway.release(req)
        priority=3

        print(id, " initiating turn-around at: ", end="")
        announceTime(env.now)
        t_ta = turnaround()
        yield env.timeout(t_ta)

        print(id, " requesting runway for take-off at: ", end=" ")
        announceTime(env.now)
        t1 = int(env.now)
        yield req
        t2 = int(env.now)
        if t1 != t2:
            print("No runways ready when requested.")
            print("Had to wait ", int(t2-t1), " seconds")


        #yield dTruck.request(env)
        print("Ops, ", id, " need deicing. Starting deicing now.")
        yield env.timeout(t_deicing)
        #dTruck.release(env)
        print(id, "Finished deicing. Initiating take-off at: ", end=" ")
        announceTime(env.now)
        yield env.timeout(t_takeoff)
        runway.release(req)

        print(id, " airborne at: ", end="")
        announceTime(env.now)



# Starting to add plots
# Firstly, we need an array with results of arriving planes

def noInterArrivalTimes(T_interarrival):
    amountOfArrivals = [0, 0, 0, 0, 0]

    for arrivaltime in scheduled_interarrivals:
        if arrivaltime == 60:
            amountOfArrivals[0] += 1
        elif 60 < arrivaltime < 120:
            amountOfArrivals[1] += 1
        elif 120 < arrivaltime < 180:
            amountOfArrivals[2] += 1
        elif 180 < arrivaltime < 240:
            amountOfArrivals[3] += 1
        elif arrivaltime > 240:
            amountOfArrivals[4] += 1

    timeIntervals = ("60s", "60-120s", "120-180s","180-240", "> 240s")
    plt.bar(timeIntervals, amountOfArrivals, align="center")
    plt.xlabel("Interarrival time intervals")
    plt.ylabel("Amount of planes")
    plt.title("Amount of planes landing and within which interarrival interval")
    plt.show()

def pltLandingPlanes():
    results = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    for x in actual_interarrivals:
        results[x] += 1

    plt.bar([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23], results, width=0.9, align="center")

    plt.xlabel("Time in hours")
    plt.ylabel("Planes")
    plt.title("Amount of planes landing each hour")
    plt.show()


env.process(plane_generator(env, 60))
env.process(badWeather(env, 1))
env.run(3600*24*7)
noInterArrivalTimes(scheduled_interarrivals)
pltLandingPlanes()

