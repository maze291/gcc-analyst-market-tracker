# Careerjet Source Rule

## Week 0 Role

Active feasibility-test source alongside JSearch.

## Production Status

Possible production candidate only after terms clarification. The publisher API supports retrieving job results, but aggregate analytics and storage rights must be confirmed.

## Technical Notes

- UAE endpoint documentation: https://www.careerjet.ae/partners/api
- Saudi endpoint documentation: https://www.careerjet.com.sa/partners/api
- Expected locales: `en_AE` and `en_SA`
- Requests require Basic authentication with the API key as username and an empty password.
- The current endpoint is `https://search.api.careerjet.net/v4/query`.
- Requests require `user_ip` and `user_agent`; the fetcher also sends a publisher-style `Referer` header.

## Use Constraints

- Keep raw responses local-only.
- Store source domain only from `site` or parsed `url`.
- Treat `description` as snippet text for temporary skill extraction only.
- Do not publish Careerjet listing text unless permission explicitly allows it.
