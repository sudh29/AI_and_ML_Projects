import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn
import sklearn.cluster as cluster
import sklearn.metrics as metrics
import sklearn.preprocessing as preprocessing
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# you can access datasets by calling:
data_train = pd.read_csv("data_train.csv")
data_test = pd.read_csv("data_test.csv")


def cluster_customers(data_train, data_test):

    # Train data
    df_train = pd.DataFrame(data_train)
    # y_train=df_train['cluster']
    df_train.drop(['cluster'], axis=1,inplace=True)
    # print(df_train)
    # print(df_train.describe())
    # seaborn.pairplot(df_train[['account_1','account_2']])
    # plt.show()

    # Test data
    df_test = pd.DataFrame(data_test)
    y_test=df_test['cluster']
    df_test.drop(['cluster'], axis=1,inplace=True)
    # print(df_test)
    
    # Standardize data
    # pd.DataFrame(ss.fit_transform(df),columns = df.columns)

    scaler = StandardScaler()
    sd_train = scaler.fit_transform(df_train)
    sd_test = scaler.fit_transform(df_test)
    sd_train = pd.DataFrame(sd_train.round(3),columns = df_train.columns)
    # print(sd_train)
    sd_test = pd.DataFrame(sd_test.round(3), columns=df_test.columns)
    # print(sd_test)

    #kmeans
    K=range(2,11)
    wcss_list=[]
    for i in K:
        km = KMeans(
        n_clusters=i, init='k-means++',
        n_init=10, max_iter=50, 
        tol=0.05, random_state=0)
        kmeans=km.fit(sd_train)
        wss_iter = kmeans.inertia_
        wcss_list.append(wss_iter)
    # print(wcss_list)
    cluster_wss=pd.DataFrame({'cluster':K,'wss': wcss_list})
    # seaborn.scatterplot(x = 'cluster', y = 'wss' , data = cluster_wss , markers="+")
    # plt.show()

    for i in range(8):
        # print(wcss_list[i],wcss_list[i+1],wcss_list[i]-wcss_list[i+1],i+2)
        if (wcss_list[i]-wcss_list[i+1]) <20:
            optimal_cluster=i+2
            break
    # print(optimal_cluster)

    # optimal
    km_opt = KMeans(
        n_clusters=optimal_cluster, init='k-means++',
        n_init=10, max_iter=50, 
        tol=0.05, random_state=0)
    kmeans_opt=km_opt.fit(sd_train)
    df_train_opt=sd_train
    df_train_opt['cluster']=kmeans_opt.labels_
    # print(df_train_opt)

    km_4 = KMeans(
        n_clusters=4, init='k-means++',
        n_init=10, max_iter=50, 
        tol=0.05, random_state=0)
    kmeans_4=km_4.fit(sd_train)
    df_train_4=sd_train
    df_train_4['cluster']=kmeans_4.labels_
    # print(df_train_4)
    
    # Silhouette score for k(clusters)
    # for i in range(2,11):
    #     labels=KMeans(n_clusters=i,random_state=0).fit(sd_train).labels_
    #     print ("Silhouette score for k(clusters) = "+str(i)+" is "
    #        +str(metrics.silhouette_score(sd_train,labels,metric="euclidean",sample_size=1000,random_state=0)))

    # Silhouette score for kmeans_opt and sd_train
    labels=kmeans_opt.labels_
    silhouette_score_opt = metrics.silhouette_score(sd_train,labels,metric="euclidean",sample_size=1000,random_state=0)
    # print(silhouette_score_opt)

    # Silhouette score for kmeans_4 and sd_train
    labels=kmeans_4.labels_
    silhouette_score_4 = metrics.silhouette_score(sd_train,labels,metric="euclidean",sample_size=1000,random_state=0)
    # print(silhouette_score_4)

    # Silhouette score for kmeans_4 and sd_test
    labels=km_4.fit(sd_test).labels_
    silhouette_score_4_test = metrics.silhouette_score(sd_test,labels,metric="euclidean",sample_size=1000,random_state=0)
    # print(silhouette_score_4_test)

    # Based on kmeans_opt and sd_test
    test_kmeans = kmeans_opt.fit(sd_test)
    labels_predicted = test_kmeans.labels_
    # print(labels_predicted)

    # first observation from sd_test
    first_ob = (sd_test[0:1]).to_numpy()  
    cluster_centers = pd.DataFrame(test_kmeans.cluster_centers_ ,columns = df_train.columns).to_numpy()

    max_opt_dist={}
    euclidean_dist = []
    for i in range(6):
        #calculate Euclidean distance between the two vectors 
        e_distance=np.sqrt(np.sum(np.square(np.subtract(cluster_centers[i],first_ob))))
        #calculate Euclidean distance between the two vectors using numpy
        # e_distance2=np.linalg.norm(arr2[i]-arr1)
        euclidean_dist.append(e_distance)
        max_opt_dist[e_distance]=i
    # print(max_opt_dist)
    euclidean_dist.sort(reverse=True)
    max_opt=[ max_opt_dist[i] for i in euclidean_dist]
    # print(max_opt)
    
    return {
        "sd_train": sd_train,
        "sd_test": sd_test,
        "wcss": wcss_list,
        "kmeans_opt": kmeans_opt,
        "silhouette": silhouette_score_opt,
        "completeness": (silhouette_score_4, silhouette_score_4_test),
        "labels_predicted": labels_predicted,
        "max_opt": max_opt,
    }


final_result = cluster_customers(data_train,data_test)
print("************* Output ***************")
for k, v in final_result.items():
    print(k)
    print(v)
    print("----------------------------------------------------")
