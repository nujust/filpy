program main
  implicit none

  character filfile*400, idfile*400, datafile*400, timefile*400
  character outkey_char*4, var_size_char*3, eid_char*16
  logical :: flg = .false.
  integer(8) i,j,k,count,idcount
  integer(8) :: chunk(512), record(512)
  integer(8) outkey, id, word, length, key, offset, id_size, var_size
  integer(8) total_time, step_time, procedure_type, step, increment
  integer(8),allocatable :: id_array(:), values(:,:)
  integer(8) :: nan = 9223372036854775615  !倍精度浮動小数点数に変換するとnanになる整数
  integer(8) :: elem_keys(14) = (/13,495,496,497,498,499,500,501,502,503,504,505,506,507/)
  integer(8) :: node_keys(5) = (/101,102,103,104,107/)

  call getarg(1, filfile)         ! 第1引数:filファイル
  call getarg(2, outkey_char)     ! 第2引数:出力するレコードキーの番号
  read(outkey_char,*) outkey
  call getarg(3, var_size_char)   ! 第3引数:変数の成分の数
  read(var_size_char,*) var_size
  call getarg(4, idfile)          ! 第4引数:出力する節点/要素番号が記されたファイル
  call getarg(5, datafile)        ! 第5引数:抽出データの出力先のバイナリファイル
  call getarg(6, timefile)        ! 第6引数:時刻データの出力先のバイナリファイル

  open(100,file=trim(idfile),status='old')
  id_size = 0
  do
    read(100,*,end=900)
    id_size = id_size + 1
  end do
900 allocate(id_array(1:id_size))
  rewind (100)
  do i = 1, id_size
    read(100,*) id_array(i)
  end do
  close(100)

  allocate(values(1:id_size,1:var_size))

  open(101, file=trim(filfile), form='unformatted', status='old')
  open(102, file=trim(datafile), form='unformatted', status='replace')
  open(103, file=trim(timefile), form='unformatted', status='replace')
  count = 0
  idcount = 0
  do
    read(101,end=901) chunk
    do i = 1, 512
      count = count + 1
      word = chunk(i)
      if (count == 1) then
        length = word
        record = nan
      else if (count == 2) then
        key = word
      else
        record(count-2) = word
        if (count == length) then
          count = 0
          if(key == 2000) then
            total_time = record(1)
            step_time = record(2)
            procedure_type = record(5)
            step = record(6)
            increment = record(7)
            if((1<=procedure_type) .and. (procedure_type<=17)) then
              values = nan
              flg=.true.
            end if

          else if(key == 1) then
            ! 要素番号は4バイト整数として記録されているため、8バイト整数をトリミングして取得
            write(eid_char,'(Z16)') record(1)
            read (eid_char(9:16),'(Z8)') id

          else if((key == outkey) .and. (flg)) then
            if(value_in_array(node_keys, outkey)) then ! 節点変数
              id=record(1)
              offset=1
            else if(value_in_array(elem_keys, outkey)) then ! 要素変数
              offset=0
            end if
            if(value_in_array(id_array, id)) then
              idcount = idcount + 1
              do j=1,var_size
                values(idcount,j) = record(j+offset)
              end do
            end if

          else if((key == 2001).and.(flg)) then
            write(102) (values(k, :), k = 1,id_size)
            write(103) total_time, step_time, step, increment
            flg=.false.
            idcount = 0
          end if
        end if
      end if
    end do
  end do
901 close(101)
  close(102)
  close(103)

  stop
contains

  function value_in_array(array, value) result(flag)
    implicit none
    integer(8) :: i, value, array(:)
    logical flag
    flag = .false.
    do i = 1, ubound(array,1)
      if (array(i) == value) then
        flag = .true.
      end if
    end do
    return
  end function

end program main
