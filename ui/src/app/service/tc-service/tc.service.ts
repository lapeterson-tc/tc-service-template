import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

@Injectable({
    providedIn: 'root',
})
export class TcService {
    apiUrl: string = `//api/v3`;

    constructor(private http: HttpClient) {}

    public getOwners() {
        return this.http.get<any>(`${this.apiUrl}/security/owners`);
    }

    getUserInfo(id: number) {
        ///api/v3/security/users/1
        return this.http.get<any>(`${this.apiUrl}/security/users/${id}`);
    }
}
