#include <bits/stdc++.h>
using namespace std;

#include "RandomGen.cpp"

int main(){

    int n = 10;

    vector<pair<int,int>> locations = RandomGraph(n);

    vector<vector<double>> Distance = DistMat(locations);

    vector<int> perm(n);

    for(int i = 0 ;i < n ; i++){
        perm[i] = i;
    }

    int ans = INT32_MAX;
    
    vector<int> best(n);

    do {
        int cur = 0;
        for(int i = 0 ; i < n ; i++){
            cur += Distance[perm[i%n]][perm[(i+1)%n]];
        }
        if(cur < ans){
            ans = cur;
            for(int i = 0 ; i <n ; i++){
                best[i] = perm[i];
            }
        }
    } while (next_permutation(perm.begin(), perm.end()));


    for(int i = 0 ; i < n ; i++){
        cout<<best[i]<<" ";
    }
    cout<<"\n";
    cout<<ans<<"\n";

    
    {
        ofstream f("nodes.csv");
        for (auto &p : locations) {
            f << p.first << "," << p.second << "\n";
        }
    }

    
    {
        ofstream f("tour.txt");
        for (int i = 0; i < n; i++) {
            if (i) f << ' ';
            f << best[i];
        }
        f << "\n";
    }



    


    return 0;
}