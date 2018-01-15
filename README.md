# school_redistricting

Given input data (attendance area polygons, school capacities, school points, and attendance area enrollment) for each school level,
this script will attempt to assign attendance areas in a balanced manner.

The main loop is split into two phases: initial assignment and rebalancing.

The current iteration of this script (with only one iteration) does not create islands,
but also does not completely balance school capacities or always fall within target limits.

Current console output:

```
school_name, current_school_population, new_school_population, school_capacity, current_school_utilization, new_school_utilization
Laurel Woods ES, 671, 895, 640, 104, 139
Deep Run ES, 542, 1012, 772, 70, 131
St Johns Lane ES, 627, 776, 612, 102, 126
Waterloo ES, 619, 805, 663, 93, 121
Jeffers Hill ES, 456, 502, 421, 108, 119
Waverly ES, 778, 845, 738, 105, 114
Gorman Crossing ES, 665, 831, 735, 90, 113
Phelps Luck ES, 586, 681, 616, 95, 110
Hollifield Station ES, 719, 754, 694, 103, 108
Hammond ES, 631, 699, 653, 96, 107
Ducketts Lane ES, 536, 824, 770, 69, 107
Worthington ES, 601, 629, 590, 101, 106
Northfield ES, 642, 743, 700, 91, 106
Talbott Springs ES, 396, 396, 377, 105, 105
Clemens Crossing ES, 468, 550, 521, 89, 105
Fulton ES, 821, 817, 788, 104, 103
Guilford ES, 496, 476, 465, 106, 102
Thunder Hill ES, 557, 516, 509, 109, 101
Veterans ES, 887, 806, 821, 108, 98
Longfellow ES, 560, 498, 512, 109, 97
Cradlerock ES, 459, 390, 398, 115, 97
Centennial Lane ES, 737, 629, 647, 113, 97
Bollman Bridge ES, 570, 649, 666, 85, 97
Swansfield ES, 631, 586, 621, 101, 94
Forest Ridge ES, 671, 675, 713, 94, 94
Stevens Forest ES, 403, 372, 399, 101, 93
Elkridge ES, 837, 707, 760, 110, 93
Bryant Woods ES, 278, 337, 361, 77, 93
West Friendship ES, 280, 374, 414, 67, 90
Running Brook ES, 381, 464, 515, 73, 90
Rockburn ES, 539, 581, 653, 82, 88
Pointers Run ES, 680, 644, 744, 91, 86
Dayton Oaks ES, 649, 683, 788, 82, 86
Manor Woods ES, 557, 569, 681, 81, 83
Lisbon ES, 448, 438, 527, 85, 83
Atholton ES, 434, 345, 424, 102, 81
Clarksville ES, 545, 480, 612, 89, 78
Ilchester ES, 698, 443, 653, 106, 67
Triadelphia Ridge ES, 552, 380, 581, 95, 65
Bushy Park ES, 823, 495, 766, 107, 64
Bellows Spring ES, 553, 270, 751, 73, 35
Patapsco MS, 668, 761, 643, 103, 118
Ellicott Mills MS, 702, 831, 701, 100, 118
Oakland Mills MS, 450, 592, 506, 88, 116
Dunloggin MS, 605, 650, 565, 107, 115
Patuxent Valley MS, 707, 840, 760, 93, 110
Burleigh Manor MS, 785, 861, 779, 100, 110
Bonnie Branch MS, 742, 689, 662, 112, 104
Wilde Lake MS, 643, 771, 760, 84, 101
Murray Hill MS, 594, 669, 662, 89, 101
Mayfield Woods MS, 668, 791, 798, 83, 99
Glenwood MS, 552, 515, 545, 101, 94
Harpers Choice MS, 496, 463, 506, 98, 91
Mount View MS, 787, 719, 798, 98, 90
Clarksville MS, 665, 578, 643, 103, 89
Lake Elkhorn MS, 630, 565, 643, 97, 87
Folly Quarter MS, 715, 576, 662, 108, 87
Hammond MS, 587, 510, 604, 97, 84
Elkridge Landing MS, 764, 570, 779, 98, 73
Lime Kiln MS, 607, 484, 701, 86, 69
Thomas Viaduct MS, 514, 446, 701, 73, 63
Hammond HS, 1149, 2073, 1220, 94, 169
Long Reach HS, 1538, 2504, 1488, 103, 168
Howard HS, 1426, 1915, 1420, 100, 134
Mt Hebron HS, 1399, 1729, 1400, 99, 123
Oakland Mills HS, 1326, 1204, 1400, 94, 86
River Hill HS, 1484, 1234, 1488, 99, 82
Glenelg HS, 1564, 1166, 1420, 110, 82
Centennial HS, 1302, 1117, 1360, 95, 82
Wilde Lake HS, 1359, 1045, 1424, 95, 73
Atholton HS, 1319, 914, 1460, 90, 62
Marriotts Ridge HS, 1429, 974, 1615, 88, 60
Reservoir HS, 1478, 898, 1551, 95, 57
```
