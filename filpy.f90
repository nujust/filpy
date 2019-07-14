      subroutine abqmain
      include 'aba_param.inc'

      ! 読み込み用変数
      dimension array(513), jrray(nprecd,513),lrunit(2,1)
      equivalence (array(1),jrray(1,1))
      character fname*80

      ! ユーザー定義変数
      character idfile*80,outfile*80
      logical :: flg=.false.
      logical :: idflg(10000000)=.false.
      integer outkey,id
      real value(6)

      read *, fname    ! 入力ファイル指定
      read *, outkey   ! キー指定
      read *, idfile   ! 番号リストファイル

      ! 初期化
      nru=1
      lrunit(1,1)=8
      lrunit(2,1)=2
      loutf=0
      call initpf(fname,nru,lrunit,loutf)
      junit=8
      call dbrnu(junit)

      ! 出力判定用配列の設定
      open(110,file=idfile,status='old')
      do
        read(110,*,end=1001) id
        idflg(id)=.true.
      end do
 1001 close(110)

      print '("reading ", a, ".fil")', trim(adjustl(fname))
      open(102, file = 'filpy.log', status = 'replace')
      do k1 = 1,2147483647

        ! レコードの読み込み
        call dbfile(0,array,jrcd)
        if(jrcd /= 0) exit
        key=jrray(1,2)

        ! インクリメントの開始
        if(key == 2000) then
          t_time = array(3) ! total time
          s_time = array(4) ! step time
          k_type=jrray(1,7) ! procedure type
          k_step=jrray(1,8) ! step number
          k_inc =jrray(1,9) ! increment number
          if((1<=k_type) .and. (k_type<=17)) then
            flg=.true.
            write(outfile,'(i4.4, "-", i6.6, ".txt")') k_step,k_inc
            open(101, file = outfile, status = 'replace')
          end if

        ! 要素変数
        else if(key == 1) then
          id=jrray(1,3)

        ! 指定キー出力
        else if((key == outkey) .and. (flg)) then

          ! 節点変数
          if((101<=outkey) .and. (outkey<=104)) then
            id=jrray(1,3)
            k=3
          ! 要素積分点変数
          else if((outkey==11) .or. (outkey==89)) then
            k=2
          ! 要素断面変数
          else if((outkey==13) .or. (outkey==29)) then
            k=2
          ! コネクタ要素
          else if((495<=outkey) .and. (outkey<=507)) then
            k=2
          end if

          if(idflg(id)) then
            do j=1,6
              value(j)=array(k+j)
            end do
            write(101,1002) id, value(1), value(2), value(3), value(4), value(5), value(6)
          end if

        ! インクリメントの終了
        else if((key == 2001).and.(flg)) then
          flg=.false.
          close(101)
          write(102, 1003) outfile,k_step, k_inc, t_time, s_time

        end if
      end do
      close(102)
      stop

      ! 出力フォーマット
 1002 format(i8, 6e16.8e2)
 1003 format(a16, 2i10, 2e16.8e2)
      end
