# Submission checklist

None of these are done yet; tick them as you complete them.

## 1. Make it work locally
- [ ] `cd backend && pip install -r requirements-dev.txt && pytest` – all green (includes the API tests not run in the build sandbox)
- [ ] `cd frontend && npm install && npm run lint && npm run typecheck && npm run build` – no errors (fix anything reported)
- [ ] `docker compose up --build` – open http://localhost:18080 and check all three pages show real January data
- [ ] `scripts/smoke_test.sh http://localhost:8000` passes
- [ ] Eyeball a few numbers (one day in the Explorer: check the publish time is ≤ the cutoff)

## 2. Public application
- [ ] Backend deployed (Render/other), `/api/health` returns ok
- [ ] Frontend deployed on Vercel with `VITE_API_BASE_URL` set
- [ ] Backend `CORS_ORIGINS` set to the Vercel URL; all three pages load data (no CORS errors in the browser console)
- [ ] Open the app shortly before submitting so the free-tier backend is awake
- [ ] Public URL written into README

## 3. GitHub repository
- [ ] **Public** repo with an **anonymous name** (random string, e.g. `kjhwr`)
- [ ] No personal info or secrets committed (`git grep -i -E "password|token|@gmail"`; `.env` is git-ignored)
- [ ] README complete: file/directory description, how to start, deployed link, AI-tools disclosure (edit the disclosure to list every tool you used)
- [ ] Commit author name/email are not identifying (or use the anonymous GitHub noreply email)

## 4. Video (unlisted YouTube, ≤ 10 minutes total)
- [ ] Part 1 – customer presentation, ≤ 5 min (`docs/customer-demo-script.md`)
- [ ] Part 2 – technical walkthrough, ≤ 5 min (`docs/technical-demo-script.md`)
- [ ] Total length ≤ 10:00; audio and screen readable
- [ ] Visibility set to **Unlisted**

## 5. Verify every URL in an incognito window
- [ ] Deployed app opens without login
- [ ] GitHub repo opens without login
- [ ] YouTube video plays without login

## 6. Submit
- [ ] Complete the official "Full Stack SWE challenge submission v4" form with the app URL, repo URL and video URL
- [ ] Keep a copy of the confirmation
