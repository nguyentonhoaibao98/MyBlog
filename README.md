# BC Notes

An English-language knowledge library for Dynamics 365 Business Central.

## Features

- Admin access code with an HTTP-only session cookie and login rate limiting.
- Public library limited to articles explicitly published by the Admin.
- PDF uploads up to 20 MB that create articles with a title, description, category, and optional notes.
- Edit, delete, search, and change article visibility.
- Server-side authorization for private articles and their PDF files.
- Persistent Cloudflare D1 records and R2 document storage.

PDFs are embedded for reading; their contents are not automatically converted into article text.

## Local development

Requires Node.js 22.13 or newer.

1. Run `npm run install:ci`.
2. Create an ignored `.dev.vars` file containing `ADMIN_CODE=<your-local-access-code>`.
3. Run `npm run build` to generate the local Wrangler configuration.
4. Apply the database schema:

```sh
node --import ./scripts/sites-env.mjs ./node_modules/wrangler/bin/wrangler.js d1 execute DB --local --config dist/server/wrangler.json --persist-to .wrangler/state --file drizzle/0000_clean_franklin_storm.sql
```

5. Run `npm run dev` and open the printed local URL.

## Deployment

The application uses the Sites Vinext runtime. `.openai/hosting.json` declares D1 binding `DB` and R2 binding `BUCKET`. Set `ADMIN_CODE` as a server-side runtime secret and deploy again after changing it. The production access code is never stored in this repository.

Database records, uploaded PDFs, and production secrets are separate from the source repository. They are not backed up by a source push.

## Verification

- `npx tsc --noEmit`
- `npm run build`
- `node scripts/check-access.mjs` against a disposable local database and a local `ADMIN_CODE=local-test-only`. The test creates and removes its own temporary article and file.
