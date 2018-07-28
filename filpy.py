
import os
import pandas as pd


def histdata(panel, id):
    df = panel.major_xs(id).T
    df.index.names = ('step', 'increment', 'total time', 'step time')
    return df

labels = ('id', 'Component-1', 'Component-2', 'Component-3', 'Component-4', 'Component-5', 'Component-6')
dict = {}
time= {}

logfile = 'filpy.log'
for line in open(logfile, 'r'):
    linedata = line.split()

    file = linedata[0]
    step = int(linedata[1])
    increment = int(linedata[2])
    t_time = float(linedata[3])
    s_time = float(linedata[4])

    index = (step, increment, t_time, s_time)
    time[(step, increment)] = index
    dict[index] = pd.read_table(file, sep='\s+', names=labels, index_col=0)
    os.remove(file)
    print(f"creating panel step {step} increment {increment}\r", end="")

print()
os.remove(logfile)
panel = pd.Panel(dict)
print(panel)

ProgramList = ('EXIT', 'History', 'Index', 'Max', 'Min')
for i, Program in enumerate(ProgramList):
    print(f" {i}:{Program}")

while True:
    try:
        ProgramNo = int(input("Enter program number --> "))
        print(ProgramList[ProgramNo])
        if ProgramNo == 0:
            break

        elif ProgramNo == 1:
            for id in panel.axes[1]:
                outfile = f"data_history({id}).csv"
                histdata(panel, id).to_csv(outfile, index=True)
                print('Out to', outfile)

        elif ProgramNo == 2:
            step = int(input("Enter step --> "))
            increment = int(input("Enter increment --> "))
            outfile = f"data_index({step}-{increment}).csv"
            panel[time[(step, increment)]].to_csv(outfile)
            print('Out to', outfile)

        elif ProgramNo == 3:
            outfile = "data_max.csv"
            panel.max(axis=0).to_csv(outfile)
            print('Out to', outfile)

        elif ProgramNo == 4:
            outfile = "data_min.csv"
            panel.min(axis=0).to_csv(outfile)
            print('Out to', outfile)

    except:
        print('ERROR: invalid value')
        continue
