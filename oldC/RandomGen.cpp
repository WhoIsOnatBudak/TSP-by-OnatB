#include <bits/stdc++.h>
using namespace std;

vector<pair<int,int>> RandomGraph(int n){

    srand(time(0));

    vector<pair<int,int>> locations;

    for(int i = 0 ; i < n ; i++){
        int x = rand() % 600;
        int y = rand() % 600;
        locations.push_back({x,y});
    }
 

    return locations;
}


vector<vector<double>> DistMat(vector<pair<int,int>> locations){
    int n = locations.size();

    vector<vector<double>> DistanceMatrix(n,vector<double>(n,0.0));

    for(int i = 0 ; i < n ; i++ ){
        for(int j = 0 ; j < n ; j++){
            int x_dist = locations[i].first - locations[j].first;
            int y_dist = locations[i].second - locations[j].second;
            DistanceMatrix[i][j] = sqrt(1.0 * x_dist*x_dist + 1.0*y_dist*y_dist);
        }
    }

    return DistanceMatrix;
}