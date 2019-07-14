# -*- coding: utf-8 -*-

import sys, argparse, time
from struct import unpack

import numpy as np, pandas as pd
from output import output_operation

def bytes_to_int(bytes_value):
    return int.from_bytes(bytes_value, 'little')

def bytes_to_float(bytes_value):
    return unpack('<d', bytes_value)[0]

def records_from_file(filfile):
    # ファイルから1レコードずつ生成するジェネレータ
    
    WORD_NUM = 512
    WORD_SIZE = 8
    DATA_SIZE = WORD_NUM * WORD_SIZE
    HEADER_SIZE = 4
    FOOTER_SIZE = 4
    CHUNK_SIZE = HEADER_SIZE + DATA_SIZE + FOOTER_SIZE
    
    int_from_bytes = int.from_bytes
    count = 0
    with open(filfile,"rb") as fp:
        fp_read = fp.read
        while True:
            chunk = fp_read(CHUNK_SIZE)
            if not chunk: break
            data = chunk[HEADER_SIZE:-FOOTER_SIZE]
            for slice_index in range(0, DATA_SIZE, WORD_SIZE):
                word = data[slice_index:slice_index+WORD_SIZE]
                count += 1
                if count == 1:
                    record = []
                    record_append = record.append
                    length = int_from_bytes(word, 'little')
                elif count == 2:
                    key = int_from_bytes(word, 'little')
                else:
                    record_append(word)
                    if count == length:
                        count = 0
                        yield key, record

def make_dataframe(filfile, outkey, setname):
    # 指定したキーと節点/要素番号にヒットする値からDataFrameを生成
    
    # 出力に対応するキー
    elem_keys = {11:'S',
                 13:'SF',
                 29:'SE',
                 89:'LE',
                 495:'CTF',
                 496:'CEF',
                 497:'CVF',
                 498:'CSF',
                 499:'CSLST',
                 500:'CRF',
                 501:'CCF',
                 502:'CP',
                 503:'CU',
                 504:'CCU',
                 505:'CV',
                 506:'CA',
                 507:'CFAILST'}
    node_keys = {101:'U',
                 102:'V',
                 103:'A',
                 104:'RF'}
    
    # 節点変数か要素変数かで抽出処理を分岐
    if outkey in elem_keys:
        OUTTYPE = 'element'
        VARTYPE = elem_keys[outkey]
        extract_func = lambda record: list(map(bytes_to_float, record[0:6]))
    elif outkey in node_keys:
        OUTTYPE = 'node'
        VARTYPE = node_keys[outkey]
        extract_func = lambda record: list(map(bytes_to_float, record[1:7]))
    else:
        raise KeyError()

    time_list = []
    var_list = [f'{VARTYPE}{i}' for i in range(1,7)]

    valid_step = False # 抽出のオンオフの切り替え
    init_flag = True # 初期化実行用

    whole_arr = [] # 出力値格納用
    id_lists = {} # 節点/要素集合格納用

    for key, record in records_from_file(filfile):
        if key == 2000: # インクリメントの開始
            if init_flag: # 抽出対象の節点/要素番号を設定し，配列のサイズを定義
                init_flag = False
                if not setname in id_lists:
                    print(f"ERROR: '{setname}' is not exist in {OUTTYPE} sets. Please enter one from following set names.")
                    for set_name in id_lists.keys():
                        print(set_name)
                    sys.exit()
                id_list = id_lists[setname]
                id_set = set(id_list)
                internal_id_index = {key:i for i, key in enumerate(id_list)}
                inc_arr_nan = np.full([len(id_list), len(var_list)], np.nan) # 配列初期化用
            total_time, step_time = map(bytes_to_float, record[0:2])
            procedure_type, step, increment = map(bytes_to_int, record[4:7])
            time = (step, increment, total_time, step_time)
            if procedure_type in {1, 2, 4, 5, 11, 12, 13, 17, 21, 22}:
                valid_step = True
                inc_arr = inc_arr_nan.copy() # インクリメントごとデータの格納用配列

        elif key == 1 and valid_step: # 要素変数
            id_num = bytes_to_int(record[0][:4])

        elif key == outkey and valid_step:
            if OUTTYPE == 'node':
                id_num = bytes_to_int(record[0])
            if id_num in id_set:
                inc_arr[internal_id_index[id_num]] = extract_func(record)

        elif key == 2001 and valid_step: # インクリメントの終了
            valid_step = False
            if not np.isnan(inc_arr).all():
                whole_arr.append(inc_arr)
                time_list.append(time)
                print(f"\rstep:{step:>3} increment:{increment:>6}", end="")

        elif key == 1931 and OUTTYPE == 'node': # 節点集合
            id_list_name = record[0].decode().strip()
            if id_list_name.isdecimal():
                id_list_name = int(id_list_name)
            id_lists[id_list_name] = list(map(bytes_to_int, record[1:]))

        elif key == 1932 and OUTTYPE == 'node': # 節点集合つづき
            id_lists[id_list_name].extend(map(bytes_to_int, record))

        elif key == 1933 and OUTTYPE == 'element': # 要素集合
            id_list_name = record[0].decode().strip()
            if id_list_name.isdecimal():
                id_list_name = int(id_list_name)
            id_lists[id_list_name] = list(map(bytes_to_int, record[1:]))
            
        elif key == 1934 and OUTTYPE == 'element': # 要素集合つづき
            id_lists[id_list_name].extend(map(bytes_to_int, record))

        elif key == 1940: # ラベル相互参照
            reference_id = bytes_to_int(record[0][:4])
            string = ''.join(map(lambda word: word.decode().strip(), record[1:]))
            if reference_id in id_lists:
                id_lists[string] = id_lists.pop(reference_id)

    if len(whole_arr) == 0:
        print(f"ERROR: {VARTYPE} values not found in {setname}")
        sys.exit()
    whole_arr = np.array(whole_arr).reshape(len(whole_arr), -1)
    df_index = pd.MultiIndex.from_arrays(list(zip(*time_list)), names=('Step', 'Increment', 'Total time', 'Step time'))
    df_columns = pd.MultiIndex.from_product([id_list,var_list], names=('ID', 'Variable'))
    df = pd.DataFrame(whole_arr, index=df_index, columns=df_columns)
    return df

def main():
    now_time = time.time()
    parser = argparse.ArgumentParser()
    parser.add_argument('filfile', help='fil file', type=argparse.FileType('r'))
    parser.add_argument('outkey', help='key number', type=int)
    parser.add_argument('setname', help='nset/elset name', type=str)
    args = parser.parse_args()
    filfile = args.filfile.name
    outkey = args.outkey
    setname = args.setname

    df = make_dataframe(filfile, outkey, setname)
    elapsed_time = time.time() - now_time
    print(f" - extracting time: {elapsed_time:.5f}")
    print('--- extracted data ---')
    print(f'Time: {len(df.index)} items', df.index.values)
    print(f'ID: {len(df.columns.levels[0])} items', df.columns.levels[0].values)
    print(f'Variable: {len(df.columns.levels[1])} items', df.columns.levels[1].values)
    print()
    output_operation(df)

if __name__ == '__main__':
    main()
