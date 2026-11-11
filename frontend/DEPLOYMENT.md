# Deploy the frontend to Vercel

## Vercel project settings

Import the repository into Vercel and set:

- **Root Directory:** `frontend`
- **Framework Preset:** Vite
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Install Command:** `npm install`

Keep `frontend/vercel.json` in place. It proxies `/api/*` to the Render API and serves the React app for client-side routes. The API proxy keeps authentication cookie traffic on the frontend's origin; do not change frontend API calls to use the Render hostname directly unless the backend cookie policy is also redesigned.

## Set the Render API destination

The rewrite currently targets `https://ecotrees-api.onrender.com`, matching the Render service name in the root `render.yaml`. After creating the Render service, confirm its public URL in the Render dashboard. If Render assigned another hostname or you use a custom domain, update the API rewrite destination in `frontend/vercel.json` and deploy again.

The backend's `PUBLIC_BASE_URL` and `WEBHOOK_URL` are separate: they should point to the Render API URL, with the latter ending in `/hooks/forge`.

## Deploy and verify

1. Deploy the API on Render and confirm `https://<render-api-host>/healthz` returns `{"status":"ok"}`.
2. Deploy this Vercel project. Vercel automatically uses `frontend/vercel.json`; no frontend API secret or `VITE_*` setting is required.
3. Open the Vercel deployment and test the landing page, direct navigation to a nested route (for example `/login` or `/farmer/overview`), and `/api/healthz`. The API health check should return the backend response through the proxy.
4. Verify login and logout in a browser to confirm the HttpOnly session cookie works through the same-origin rewrite.

Do not set `VITE_*` values to private credentials: Vite embeds those values into public JavaScript assets. Live payment and payout operations remain fail-closed until the bank schemas are verified.
