set terminal png
set xlabel 'Carbon Index'
set ylabel 'S_CD'
set output '/home2/jcjeong/project/stanalyzer0/stanalyzer/media/jcjeong/20131017160012817695MWxzFF/ordpara_charmm/ordpara_charmm1.png'
plot "/home2/jcjeong/project/stanalyzer0/stanalyzer/media/jcjeong/20131017160012817695MWxzFF/ordpara_charmm/ordpara_POPI_C3.dat" using 1:2 title "POPI" with lines lw 3
