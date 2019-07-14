# -*- coding: utf-8 -*-

import pandas as pd

def histid(df, id_num):
    return df.xs(id_num, level=0, axis=1)

def histvariable(df, variable):
    return df.xs(variable, level=1, axis=1)

def step_inc(df, step, increment):
    return df.xs([step, increment]).stack(0, dropna=False).reset_index([0,1], drop=True)

def output_operation(df):

    id_list = df.columns.levels[0].values
    variable_list = df.columns.levels[1].values

    print("--- Output operation ---")
    ProgramList = ('EXIT', 'History_ID', 'History_Variable', 'Index', 'Max', 'Min', 'All', 'History_ID_Excel', 'History_Variable_Excel')
    for i, Program in enumerate(ProgramList):
        print(f" {i}:{Program}")

    while True:
        try:
            ProgramNo = int(input("Enter program number --> "))
            print(ProgramList[ProgramNo])
            if ProgramNo == 0:
                break

            elif ProgramNo == 1:
                id_num = int(input("Enter id --> "))
                outfile = f"data_history({id_num}).csv"
                histid(df, id_num).to_csv(outfile)
                print('Save to', outfile)

            elif ProgramNo == 2:
                axis = int(input("Enter axis --> "))
                variable = variable_list[axis-1]
                outfile = f"data_history({variable}).csv"
                histvariable(df, variable).to_csv(outfile)
                print('Save to', outfile)

            elif ProgramNo == 3:
                step = int(input("Enter step --> "))
                increment = int(input("Enter increment --> "))
                outfile = f"data_index({step}-{increment}).csv"
                step_inc(df, step, increment).to_csv(outfile)
                print('Save to', outfile)

            elif ProgramNo == 4:
                outfile = "data_max.csv"
                df.max().unstack().to_csv(outfile)
                print('Save to', outfile)

            elif ProgramNo == 5:
                outfile = "data_min.csv"
                df.min().unstack().to_csv(outfile)
                print('Save to', outfile)

            elif ProgramNo == 6:
                outfile = 'data_all.csv'
                df.to_csv(outfile)
                print('Save to', outfile)

            elif ProgramNo == 7:
                outfile = 'data_id.xlsx'
                with pd.ExcelWriter(outfile) as writer:
                    for id_num in id_list:
                        histid(df, id_num).to_excel(writer, sheet_name=str(id_num), merge_cells=False)
                print('Save to', outfile)

            elif ProgramNo == 8:
                outfile = 'data_variable.xlsx'
                with pd.ExcelWriter(outfile) as writer:
                    for variable in variable_list:
                        histvariable(df, variable).to_excel(writer, sheet_name=variable, merge_cells=False)
                print('Save to', outfile)

        except (IndexError, KeyError):
            print('ERROR: invalid value')
            continue
