set terminal png
set xlabel 'Time (ps)'
set ylabel 'Angstrom'
set output '/home2/jcjeong/project/stanalyzer0/stanalyzer/media/jcjeong/201308011636126283543pgoOr/thickness_phosphate/thickness_phosphate0.png'
plot "/home2/jcjeong/project/stanalyzer0/stanalyzer/media/jcjeong/201308011636126283543pgoOr/thickness_phosphate/thickness_phosphate.dat" using 1:2 title "phosphate_based thicknesss" with lines lw 3
