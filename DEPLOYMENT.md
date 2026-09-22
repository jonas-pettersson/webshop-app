# Deployment Information

## Live Application

**Production URL:** https://svenska-kyrkan-webshop-reports.streamlit.app/

**Status:** ✅ Deployed and operational

**Deployment Date:** September 2026

## Deployment Details

- **Platform:** Streamlit Cloud (Free Tier)
- **Repository:** https://github.com/jonas-pettersson/webshop-app
- **Branch:** `main`
- **Main File:** `app.py`
- **Auto-Deploy:** Enabled (pushes to main trigger redeployment)

## Access

**URL:** https://svenska-kyrkan-webshop-reports.streamlit.app/

**Authentication:** Password required (configured in Streamlit Cloud secrets)

## Updating the Deployment

The app automatically redeploys when you push to GitHub:

```bash
cd webshop-app
git add .
git commit -m "Your changes"
git push
```

Streamlit Cloud will detect the push and redeploy within 2-3 minutes.

## Managing Secrets

To update the password or add new secrets:

1. Go to https://share.streamlit.io/
2. Navigate to your app: `svenska-kyrkan-webshop-reports`
3. Click on "Settings" → "Secrets"
4. Edit the secrets TOML:
   ```toml
   password = "your-secure-password"
   ```
5. Save changes (app will restart automatically)

## Optional: Custom Domain

To use your own domain with DNSimple:

1. **Get your Streamlit URL** after deployment
2. **In DNSimple**, add a CNAME record:
   - Name: `webshop` (or `reports`)
   - Value: `[app-name].streamlit.app`
3. **Access at:** `https://webshop.svenskakyrkan.at`

## Repository

- **GitHub:** https://github.com/jonas-pettersson/webshop-app
- **Branch:** main
- **Files:** 29 files, ~1,670 lines of code
- **Templates:** 12 Excel templates included
- **Documentation:** README.md, QUICKSTART.md, CLAUDE.md

## Deployment History

| Date | Commit | Description |
|------|--------|-------------|
| 2026-09-21 | 22ea1b4 | Initial deployment |
| 2026-09-22 | c76d06e | Added CLAUDE.md documentation |

## Monitoring

**Check deployment status:**
- Streamlit Cloud dashboard: https://share.streamlit.io/
- Application logs available in Streamlit Cloud console

**Performance:**
- Free tier: 1GB RAM
- Automatic sleep after 7 days inactivity
- Wakes in 5-10 seconds when accessed

## Troubleshooting

**If deployment fails:**
- Check the Streamlit Cloud logs
- Verify all dependencies in requirements.txt
- Make sure secrets are properly configured

**If the app crashes:**
- Check for import errors in the logs
- Verify template files are accessible
- Test locally first with `streamlit run app.py`

## Security Notes

- ✅ `secrets.toml` is NOT in git (gitignored)
- ✅ Only `secrets.toml.example` is tracked
- ⚠️ Change the password in Streamlit Cloud secrets
- ⚠️ Keep the repository private if it contains sensitive templates
