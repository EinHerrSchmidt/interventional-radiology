import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

sample = [60, 20, 135, 20, 60, 20, 135, 40, 20, 60, 20, 40, 15, 30, 40, 130, 60, 20, 40, 20, 20, 20, 135, 20, 20, 20, 20, 35, 50, 15, 20, 20, 40, 20, 20, 15, 100, 20, 15, 20, 20, 20, 20, 50, 20, 20, 20, 60, 20, 35, 40,
          35, 15, 15, 35, 20, 135, 20, 30, 20, 20, 20, 35, 135, 30, 30, 15, 20, 20, 20, 20, 20, 30, 20, 15, 20, 135, 135, 60, 15, 15, 20, 15, 60, 20, 20, 50, 60, 30, 15, 20, 50, 60, 135, 20, 15, 20, 30, 15, 90, 50, 30, 60, 60, 30]

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



unique, counts = np.unique(sample, return_counts=True)
print(unique)
print(counts)
frequencies = counts / sum(counts)
print(frequencies)
print(sum(frequencies))
cumulativeSum = np.cumsum(frequencies)
print(cumulativeSum)

def draw_categorical_from_sample(sample, n):
    unique, counts = np.unique(sample, return_counts=True)
    frequencies = counts / sum(counts)
    cumulativeSum = np.cumsum(frequencies)
    draws = stats.uniform.rvs(size=n)
    result = np.zeros(n) - 1
    for i in range(0, len(draws)):
        for j in range(0, len(cumulativeSum)):
            if(draws[i] <= cumulativeSum[j]):
                result[i] = unique[j]
                break
        if(result[i] == -1):
            result[i] = unique[-1]
    return result

categoricalSample = draw_categorical_from_sample(sample, 300)
print(categoricalSample)

plt.hist(categoricalSample, bins='auto')
plt.show()

plt.hist(sample, bins='auto')
plt.show()