# Privacy Policy for MorbMyth Studio

**Effective Date:** October 10, 2026  
**Last Updated:** October 10, 2026

MorbMyth Studio ("we", "our", or "us") operates as an internal automated content management tool. This Privacy Policy explains how we collect, use, and protect your information when you connect your TikTok account to our system.

---

## 1. Information We Collect
When you connect your TikTok account via TikTok Content Posting API, we may request access to:
- **Basic Profile Information:** Username, profile picture, and account ID (via `user.info.basic`).
- **Video Publishing Permissions:** Ability to upload and post videos directly to your authorized TikTok account (via `video.publish` / `video.upload`).

---

## 2. How We Use Your Information
We only use the authorized permissions to:
- Authenticate and display your connected account status on our local internal dashboard.
- Automatically publish short vertical videos (Shorts/Reels/TikToks) rendered by our automated pipeline to your official TikTok account.
- We **do not** sell, share, rent, or trade your personal data or access tokens to any third parties.

---

## 3. Data Storage and Security
- All authentication tokens (Access Token and Refresh Token) are stored locally on your private server environment (`.env` or local configuration) and are never exposed publicly.
- We implement standard security practices to ensure your credentials remain private.

---

## 4. User Rights and Data Revocation
You can revoke MorbMyth Studio's access to your TikTok account at any time by:
1. Navigating to your **TikTok App Settings**.
2. Going to **Security & Login** -> **Manage App Permissions**.
3. Removing **MorbMyth Studio** from the authorized app list.

---

## 5. Contact Us
If you have any questions or concerns regarding this Privacy Policy, please contact us at:
- **Developer / Maintainer:** MauludyZhrn
- **GitHub:** https://github.com/MauludyZhrn