import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    vus: 10,
    duration: '30s',
};

const BASE_URL = 'http://localhost:8003/predict';
const HEADERS = { 'Content-Type': 'application/json' };

export default function () {
    const itemId = Math.floor(Math.random() * 100000);

    const seedPayload = JSON.stringify({
        item_id: itemId,
        seller_id: 1,
        is_verified_seller: true,
        title: `Test Item ${itemId}`,
        description: "Good condition",
        category_id: 10,
        images_qty: 3
    });
    http.post(`${BASE_URL}/seed_test_data`, seedPayload, { headers: HEADERS });

    if (Math.random() < 0.8) {

        let resSync = http.get(`${BASE_URL}/simple_predict/${itemId}`);
        check(resSync, { 'sync predict 200': (r) => r.status === 200 });

        let resAsync = http.post(`${BASE_URL}/async_predict/${itemId}`);
        check(resAsync, { 'async predict 202': (r) => r.status === 202 });

        http.post(`${BASE_URL}/close/${itemId}`);

    } else {

        let res404 = http.get(`${BASE_URL}/simple_predict/999999999`);
        check(res404, { 'predict 404': (r) => r.status === 404 });

        const poisonPayload = JSON.stringify({
            seller_id: 1, is_verified_seller: true, item_id: itemId,
            title: "Poison", description: "POSION_PILL_67_67", category: 1, images_qty: 1
        });
        let res500 = http.post(`${BASE_URL}/`, poisonPayload, { headers: HEADERS });
        check(res500, { 'predict 500': (r) => r.status === 500 });
    }

    sleep(0.3);
}