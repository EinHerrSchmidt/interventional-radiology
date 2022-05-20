import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

x = np.random.normal(170, 10, 250)

sample = [24,
30,
30,
127,
15,
63,
55,
58,
75,
15,
23,
18,
31,
50,
84,
79,
35,
100,
32,
24,
70,
32,
33,
23,
90,
10,
50,
18,
27,
17,
14,
23,
25,
85,
92,
54,
39,
19,
19,
85,
35,
95,
40,
65,
25,
30,
34,
30,
92,
39,
22,
70,
15,
15,
86,
24,
37,
19,
33,
32,
13,
40,
37,
23,
30,
29,
43,
27,
125,
9,
128,
27,
23,
22,
86,
20,
29,
6,
97,
60,
63,
95,
30,
27,
70,
30,
34,
225,
46,
40,
77,
20,
40,
25,
130,
55,
15,
52,
66,
106,
27,
28,
35,
125,
50]

x = np.log(sample)

k2, p = stats.normaltest(x)

alpha = 1e-3

print("p = {:g}".format(p))

if p < alpha:  # null hypothesis: x comes from a normal distribution
    print("The null hypothesis can be rejected")
else:
    print("The null hypothesis cannot be rejected")

mu, std = stats.norm.fit(x)
print("Mean: {:g}\nStandard deviation: {:g}".format(mu, std))
print("Mean: {:g}\nStandard deviation: {:g}".format(np.mean(x), np.std(x)))

plt.hist(sample, bins='auto')
plt.show()