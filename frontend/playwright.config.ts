import {defineConfig} from '@playwright/test';
export default defineConfig({
  testDir:'./tests', timeout:30000, fullyParallel:false, workers:1,
  reporter:[['list'],['html',{open:'never',outputFolder:'playwright-report'}]],
  use:{baseURL:'http://127.0.0.1:8791',trace:'retain-on-failure',screenshot:'only-on-failure'},
  webServer:{command:'python ../scripts/experience_server.py',url:'http://127.0.0.1:8791/health',reuseExistingServer:false,timeout:120000},
});
