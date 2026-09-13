/* /api/requests — the Ideas discussions ranked by upvotes.

   A Cloudflare Pages Function: it runs beside the static site and is
   the one place a GitHub token lives. GitHub's GraphQL API needs a
   token even to read public discussions, and a token in a page is a
   token in everyone's browser — so the page asks here, and this asks
   GitHub with GITHUB_TOKEN from the Pages project's secrets (a
   fine-grained token with no permissions at all: public data only).
   Cached for ten minutes at the edge, so a busy page costs GitHub one
   query in that time whoever is looking.

   Answers {open, items} — open false while the repository is private
   (the query fails on it) or the token is unset, so the page can say
   the requests open with the release rather than show an error. */

const REPOSITORY = { owner: 'visualdynamics', name: 'visualdynamics' };
const CATEGORY = 'ideas';
const LIMIT = 20;
const CACHE_SECONDS = 600;

const QUERY = `
query ($owner: String!, $name: String!, $category: String!) {
  repository(owner: $owner, name: $name) {
    discussionCategory(slug: $category) { id }
    discussions(first: 100, categoryId: null, orderBy: {field: UPDATED_AT, direction: DESC}) {
      nodes {
        title url upvoteCount isAnswered
        category { slug }
        comments { totalCount }
      }
    }
  }
}`;

function ranked (nodes) {
  return nodes
    .filter(n => n.category && n.category.slug === CATEGORY)
    .sort((a, b) => b.upvoteCount - a.upvoteCount)
    .slice(0, LIMIT)
    .map(n => ({ title: n.title, url: n.url, upvotes: n.upvoteCount,
                 comments: n.comments.totalCount, answered: n.isAnswered }));
}

async function fromGitHub (token) {
  const response = await fetch('https://api.github.com/graphql', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}`,
               'Content-Type': 'application/json',
               'User-Agent': 'visualdynamics.org' },
    body: JSON.stringify({ query: QUERY, variables: { ...REPOSITORY, category: CATEGORY } })
  });
  if (!response.ok) return { open: false, items: [] };
  const body = await response.json();
  const repository = body.data && body.data.repository;
  if (!repository || !repository.discussions) return { open: false, items: [] };
  return { open: true, items: ranked(repository.discussions.nodes || []) };
}

export async function onRequestGet (context) {
  const cache = caches.default;
  const key = new Request(new URL(context.request.url).toString(), { method: 'GET' });
  const held = await cache.match(key);
  if (held) return held;
  const token = context.env.GITHUB_TOKEN;
  const answer = token ? await fromGitHub(token) : { open: false, items: [] };
  const response = new Response(JSON.stringify(answer), {
    headers: { 'Content-Type': 'application/json',
               'Cache-Control': `public, max-age=${CACHE_SECONDS}` }
  });
  context.waitUntil(cache.put(key, response.clone()));
  return response;
}

export { ranked };
