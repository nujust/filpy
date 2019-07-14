# -*- coding: utf-8 -*-

import sys
import argparse
import time
import subprocess
import os
import numpy as np
import pandas as pd

# 変数と出力キーの対応(以下に含まれる変数がこのプログラムで出力が可能)
elem_vars = {'SF': 13,
             'CTF': 495,
             'CEF': 496,
             'CVF': 497,
             'CSF': 498,
             'CSLST': 499,
             'CRF': 500,
             'CCF': 501,
             'CP': 502,
             'CU': 503,
             'CCU': 504,
             'CV': 505,
             'CA': 506,
             'CFAILST': 507}
node_vars = {'U': 101,
             'V': 102,
             'A': 103,
             'RF': 104,
             'COORD': 107}
all_vars =  {**elem_vars, **node_vars}

class bytes_word():
    def __init__(self, word):
        self.bytes = word
        
    def to_int(self):
        return int.from_bytes(self.bytes, 'little')
    
    def to_str(self):
        return self.bytes.decode().strip()

def records_from_file(filfile):
    # ファイルから1レコードずつ生成するジェネレータ
    
    def chunks_from_file(file, chunk_size):
        with open(file,'rb') as fp:
            while True:
                chunk = fp.read(chunk_size)
                if chunk:
                    yield chunk
                else:
                    break
        
    WORD_NUM = 512
    WORD_SIZE = 8
    DATA_SIZE = WORD_NUM * WORD_SIZE
    HEADER_SIZE = 4
    FOOTER_SIZE = 4
    CHUNK_SIZE = HEADER_SIZE + DATA_SIZE + FOOTER_SIZE
    
    count = 0
    for chunk in chunks_from_file(filfile, CHUNK_SIZE):
        data = chunk[HEADER_SIZE:-FOOTER_SIZE]
        for word in (bytes_word(data[idx:idx+WORD_SIZE]) for idx in range(0, DATA_SIZE, WORD_SIZE)):
            count += 1
            if count == 1:
                record = []
                length = word.to_int()
            elif count == 2:
                key = word.to_int()
                record.append(key)
            else:
                record.append(word)
                if count == length:
                    count = 0
                    yield record

def set_from_fil(filfile):
    # filファイルから節点/要素集合を取得

    nset = {}
    elset = {}
    for record in records_from_file(filfile):
        key = record[0]
        if key == 2000: # インクリメントの開始
            break

        elif key == 1931: # 節点集合
            setname = record[1].to_str()
            if setname.isdecimal():
                setname = int(setname)
            nset[setname] = [word.to_int() for word in record[2:]]

        elif key == 1932: # 節点集合つづき
            nset[setname].extend([word.to_int() for word in record[1:]])

        elif key == 1933: # 要素集合
            setname = record[1].to_str()
            if setname.isdecimal():
                setname = int(setname)
            elset[setname] = [word.to_int() for word in record[2:]]
            
        elif key == 1934: # 要素集合つづき
            elset[setname].extend([word.to_int() for word in record[1:]])

        elif key == 1940: # ラベル相互参照
            reference_id = int.from_bytes(record[1].bytes[:4], 'little')
            string = ''.join([word.to_str() for word in record[2:]])
            if reference_id in nset:
                nset[string] = nset.pop(reference_id)
            if reference_id in elset:
                elset[string] = elset.pop(reference_id)
    return nset, elset

def make_df(filfile, var_type, id_list, var_size):

    # 呼び出しを行うFortranプログラムの存在確認
    scriptdir = os.path.dirname(os.path.abspath(sys.argv[0]))
    fortran_program = os.path.join(scriptdir, 'filfort')
    if not os.path.isfile(fortran_program):
        print('ERROR:', os.path.basename(fortran_program), 'is not exist')
        sys.exit()
        
    # 節点/要素変数の判定
    if elem_vars.get(var_type):
        outtype = 'Element'
        outkey = elem_vars[var_type]
    elif node_vars.get(var_type):
        outtype = 'Node'
        outkey = node_vars[var_type]

    filfile = os.path.abspath(filfile)
    fildir = os.path.dirname(filfile)

    # 生成される一時ファイルの名前
    idfile = os.path.join(fildir, 'filpy_idlist.txt')
    datafile = os.path.join(fildir, 'filpy_datas.bin')
    timefile = os.path.join(fildir, 'filpy_times.bin')

    # Fortran入力用の節点/要素番号リストのファイルを生成
    open(idfile, 'w').write('\n'.join([str(id_num) for id_num in id_list]))

    # Fortranプログラムによりfilを読み、2つのバイナリファイルを生成
    subprocess.call([fortran_program, filfile, str(outkey), str(var_size), idfile, datafile, timefile])

    # 出力バイナリデータの読み込み
    id_size = len(id_list)
    dt = np.dtype([('head','<i'), ('data','<d', (id_size, var_size)), ('tail','<i')])
    chunk = np.fromfile(open(datafile, 'rb'), dtype=dt)
    data = chunk['data'].reshape([-1, id_size*var_size])

    # 時刻バイナリデータの読み込み
    dt = np.dtype([('head','<i'), ('total_time','<d'), ('step_time','<d'), ('step','<q'), ('increment','<q'), ('tail','<i')])
    times = np.fromfile(open(timefile, 'rb'), dtype=dt)
    
    # 一時ファイルの削除
    os.remove(idfile)
    os.remove(datafile)
    os.remove(timefile)

    # DataFrameの生成
    df_index = pd.MultiIndex.from_arrays(list(zip(*times[['step', 'increment', 'total_time', 'step_time']])),
                                         names=('Step', 'Increment', 'Total time', 'Step time'))
    var_list = [f'{var_type}{str(i).zfill(len(str(var_size)))}' for i in range(1,1+var_size)]
    df_columns = pd.MultiIndex.from_product([id_list,var_list], names=(outtype, var_type))
    df = pd.DataFrame(data, index=df_index, columns=df_columns)

    return df

def output_operation(df, savedir):
    
    def histid(df, id_num):
        return df.xs(id_num, level=0, axis=1)

    def histvariable(df, variable):
        return df.xs(variable, level=1, axis=1)

    def step_inc(df, step, increment):
        return df.xs([step, increment]).stack(0, dropna=False).reset_index([0,1], drop=True)

    id_list = df.columns.levels[0].values
    outtype = df.columns.levels[0].name
    variable_list = df.columns.levels[1].values
    vartype = df.columns.levels[1].name

    print('--- Output operation ---')
    ProgramList = ('EXIT', 'History_ID', 'History_Variable', 'Index', 'Max', 'Min', 'All')
    for i, Program in enumerate(ProgramList):
        print(f' {i}:{Program}')

    while True:
        try:
            ProgramNo = int(input('Enter program number --> '))
            print(ProgramList[ProgramNo])
            if ProgramNo == 0:
                break

            elif ProgramNo == 1:
                id_num = int(input('Enter id number (0:All) --> '))
                if id_num == 0:
                    id_iter = iter(id_list)
                else:
                    id_iter = iter([id_num])
                for id_num in id_iter:
                    filename = f'filpy_{vartype}_{outtype}{id_num}.csv'
                    savepath = os.path.join(savedir, filename)
                    histid(df, id_num).to_csv(savepath)

            elif ProgramNo == 2:
                axis = int(input('Enter axis (0:All) --> '))
                if axis == 0:
                    variable_iter = iter(variable_list)
                else:
                    variable_iter = iter([variable_list[axis-1]])
                for variable in variable_iter:
                    filename = f'filpy_{vartype}_{variable}.csv'
                    savepath = os.path.join(savedir, filename)
                    histvariable(df, variable).to_csv(savepath)

            elif ProgramNo == 3:
                step = int(input('Enter step --> '))
                increment = int(input('Enter increment --> '))
                filename = f'filpy_{vartype}_step{step}_increment{increment}.csv'
                savepath = os.path.join(savedir, filename)
                step_inc(df, step, increment).to_csv(savepath)

            elif ProgramNo == 4:
                filename = f'filpy_{vartype}_max.csv'
                savepath = os.path.join(savedir, filename)
                df.max().unstack().to_csv(savepath)

            elif ProgramNo == 5:
                filename = f'filpy_{vartype}_min.csv'
                savepath = os.path.join(savedir, filename)
                df.min().unstack().to_csv(savepath)

            elif ProgramNo == 6:
                filename = f'filpy_{vartype}_all.csv'
                savepath = os.path.join(savedir, filename)
                df.to_csv(savepath)

        except (IndexError, KeyError, ValueError):
            print('ERROR: invalid value')

def main():
    now_time = time.time() # ベンチマーク用時間計測

    # 引数処理
    parser = argparse.ArgumentParser()
    parser.add_argument('filfile', help='fil file', type=argparse.FileType('r'))
    parser.add_argument('vartype', help='key number', type=str)
    parser.add_argument('setname', help='nset/elset name', type=str)
    parser.add_argument('-v', '--varsize', help='variable components size. default=6', type=int, default=6)
    args = parser.parse_args()
    filfile = os.path.abspath(args.filfile.name)
    vartype = args.vartype.upper()
    setname = args.setname.upper()
    varsize = args.varsize

    # 有効な変数名かどうか判定
    if not all_vars.get(vartype):
        print(f'ERROR: variable type="{vartype}" is unsupported. Please enter one from following variable type.')
        print('Element variables:', *elem_vars)
        print('Node variables:', *node_vars)
        sys.exit()

    # Pythonでfilのモデル定義部を読み込み、節点/要素集合を取得
    print('reading model data...')
    nset, elset = set_from_fil(filfile)

    # 節点/要素変数の判定
    if elem_vars.get(vartype):
        id_lists = elset
    elif node_vars.get(vartype):
        id_lists = nset

    # 節点/要素番号リストの取得
    try:
        id_list = id_lists[setname]
    except KeyError:
        print(f'ERROR: setname="{setname}" is not exist. Please enter one from following set names.')
        print('\n'.join([setname for setname in id_lists.keys()]))
        sys.exit()

    print('extracting output data...')
    df = make_df(filfile, vartype, id_list, varsize)

    elapsed_time = time.time() - now_time
    print(f'extracting time: {elapsed_time:.5f}')
    print()
    print('--- extracted data ---')
    print(f'Time: {len(df.index)} items')
    print(df.index.values)
    print(f'ID: {len(df.columns.levels[0])} items')
    print(df.columns.levels[0].values)
    print(f'Variable: {len(df.columns.levels[1])} items')
    print(df.columns.levels[1].values)
    print()
    output_operation(df, os.path.dirname(filfile))

if __name__ == '__main__':
    main()
