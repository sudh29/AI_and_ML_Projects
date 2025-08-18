import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from pylab import rcParams

plt.style.use("ggplot")
# %matplotlib inline

rcParams["figure.figsize"] = 12, 8
print("dad")

data = pd.read_csv("DMV_Written_Tests.csv")
data.head()

data.info()

scores = data[["DMV_Test_1", "DMV_Test_2"]].values
results = data["Results"].values

passed = (results == 1).reshape(100, 1)
failed = (results == 0).reshape(100, 1)

ax = sns.scatterplot(
    x=scores[passed[:, 0], 0],
    y=scores[passed[:, 0], 1],
    marker="^",
    color="green",
    s=60,
)
sns.scatterplot(
    x=scores[failed[:, 0], 0], y=scores[failed[:, 0], 1], marker="X", color="red", s=60
)
ax.set(xlabel="DMV Written Test 1 Scores", ylabel="DMV Written Test 2 Scores")
ax.legend(["Passed", "Failed"])
plt.show()


def logistic_fn(x):
    return 1 / (1 + np.exp(-x))


def compute_cost(theta, x, y):
    m = len(y)
    y_pred = logistic_fn(np.dot(x, theta))
    error = (y * np.log(y_pred)) + (1 - y) * np.log(1 - y_pred)
    cost = -1 / m * sum(error)
    grad = 1 / m * np.dot(x.transpose(), (y_pred - y))
    return cost[0], grad


mean_scores = np.mean(scores, axis=0)
std_scores = np.std(scores, axis=0)
scores = (scores - mean_scores) / std_scores

rows = scores.shape[0]
cols = scores.shape[1]

X = np.append(np.ones((rows, 1)), scores, axis=1)
y = results.reshape(rows, 1)

theta_init = np.zeros((cols + 1, 1))
cost, grad = compute_cost(theta_init, X, y)

print("Cost at initializtion", cost)
print("Grad at inital", grad)


def grad_des(x, y, theta, alpha, iterations):
    costs = []
    for i in range(iterations):
        cost, grad = compute_cost(theta, x, y)
        theta -= alpha * grad
        costs.append(cost)
    return theta, costs


theta, costs = grad_des(X, y, theta_init, 1, 200)
print("Theta", theta)
print("cost", costs[-1])

plt.plot(costs)
plt.xlabel("Iterations")
plt.ylabel("$J(Theta)$")
plt.title("Cost of GD over iter")


ax = sns.scatterplot(
    x=X[passed[:, 0], 1], y=X[passed[:, 0], 2], marker="^", color="green", s=60
)
sns.scatterplot(
    x=X[failed[:, 0], 1], y=X[failed[:, 0], 2], marker="X", color="red", s=60
)
ax.legend(["Passed", "Failed"])
ax.set(xlabel="DMV Written test1", ylabel="DMV written test2")

x_boundary = np.array([np.min(X[:, 1]), np.max(X[:, 1])])
y_boundary = -(theta[0] + theta[1] * x_boundary) / theta[2]

sns.lineplot(x=x_boundary, y=y_boundary, color="blue")
plt.show()


def predict(theta, x):
    results = x.dot(theta)
    return results > 0


p = predict(theta, X)
print("Training Acurracy", sum(p == y)[0], "%")


test = np.array([50, 79])
print(test)
test = (test - mean_scores) / std_scores
print(test)
test = np.append(np.ones(1), test)


print(test)
print(theta)
prob = logistic_fn(test.dot(theta))
print("result of test", np.round(prob[0], 2), "passing", test.dot(theta))
