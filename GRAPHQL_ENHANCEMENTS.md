# GraphQL Client Enhancements - Usage Examples

## ✨ New Features Implemented

### 1. `GraphQLClient.from_url()` - Convenience Constructor

```python
from fh_saas.utils_graphql import GraphQLClient

# OLD WAY (verbose):
# from fh_saas.utils_api import AsyncAPIClient, bearer_token_auth
# async with AsyncAPIClient(url, auth_headers=bearer_token_auth(token)) as api:
#     client = GraphQLClient(api)
#     result = await client.execute_query(query)

# NEW WAY (concise):
async with GraphQLClient.from_url(
    url="https://api.quiltt.io/v1/graphql",
    bearer_token="your-session-token"
) as gql:
    result = await gql.execute(query)
```

### 2. `execute()` - Unified Query/Mutation Method

```python
# Returns only the 'data' portion (not the full GraphQL response)
async with GraphQLClient.from_url(url, bearer_token=token) as gql:
    # For queries
    users = await gql.execute("query { users { id name } }")
    
    # For mutations  
    created = await gql.execute(
        "mutation($input: CreateUser!) { createUser(input: $input) { id } }",
        variables={"input": {"name": "Alice"}}
    )
```

### 3. `execute_graphql()` - One-Liner Function

```python
from fh_saas.utils_graphql import execute_graphql

# No client management needed!
result = await execute_graphql(
    url="https://api.quiltt.io/v1/graphql",
    query="query { connections { id institution { name } } }",
    bearer_token="your-token"
)
```

### 4. `fetch_pages_relay()` - Auto-Accumulating Pagination

```python
# OLD WAY (manual pagination loop):
# all_items = []
# cursor = None
# while True:
#     result = await gql.execute(query, {"first": 100, "after": cursor})
#     edges = result['transactionsConnection']['edges']
#     all_items.extend([e['node'] for e in edges])
#     if not result['transactionsConnection']['pageInfo']['hasNextPage']:
#         break
#     cursor = result['transactionsConnection']['pageInfo']['endCursor']

# NEW WAY (automatic):
async with GraphQLClient.from_url(url, bearer_token=token) as gql:
    all_items = await gql.fetch_pages_relay(
        query='''
            query($first: Int, $after: String, $filter: Filter) {
                transactionsConnection(first: $first, after: $after, filter: $filter) {
                    edges { node { id amount date } }
                    pageInfo { hasNextPage endCursor }
                }
            }
        ''',
        connection_path="transactionsConnection",
        variables={"filter": {"status": "completed"}},
        page_size=100,
        max_pages=50  # Safety limit
    )
    print(f"Fetched {len(all_items)} total transactions")
```

## 📊 Before/After Comparison

### Fetching Paginated Data

**Before (35 lines):**
```python
from fh_saas.utils_api import AsyncAPIClient, bearer_token_auth
from fh_saas.utils_graphql import GraphQLClient

async def fetch_transactions(session_token: str, start_date: str) -> list[dict]:
    all_items = []
    cursor = None
    
    async with AsyncAPIClient(
        "https://api.quiltt.io/v1/graphql",
        auth_headers=bearer_token_auth(session_token)
    ) as api:
        gql = GraphQLClient(api)
        
        while True:
            variables = {
                "first": 100,
                "after": cursor,
                "filter": {"transactedAt": {"gte": start_date}}
            }
            result = await gql.execute_query(TRANSACTIONS_QUERY, variables)
            
            data = result.get('data', {}).get('transactionsConnection', {})
            edges = data.get('edges', [])
            page_info = data.get('pageInfo', {})
            
            for edge in edges:
                all_items.append(edge['node'])
            
            if not page_info.get('hasNextPage'):
                break
            cursor = page_info.get('endCursor')
    
    return all_items
```

**After (6 lines):**
```python
from fh_saas.utils_graphql import GraphQLClient

async def fetch_transactions(session_token: str, start_date: str) -> list[dict]:
    async with GraphQLClient.from_url(QUILTT_API_URL, bearer_token=session_token) as gql:
        return await gql.fetch_pages_relay(
            query=TRANSACTIONS_QUERY,
            connection_path="transactionsConnection",
            variables={"filter": {"transactedAt": {"gte": start_date}}}
        )
```

**Result: 83% reduction in code!**

## 🧪 Testing

All new features have comprehensive test coverage:
- ✅ `test_from_url_constructor()` - Creates working client
- ✅ `test_execute_unified_method()` - Returns data portion only
- ✅ `test_execute_graphql_one_liner()` - Standalone function works
- ✅ `test_fetch_pages_relay()` - Accumulates all pages correctly
- ✅ `test_fetch_pages_relay_max_pages()` - Respects page limits
- ✅ `test_fetch_pages_relay_with_variables()` - Passes through filters

Run tests: `nbdev_test --path nbs/08_utils_graphql_tests.ipynb`

## 📦 Implementation Details

- Modified notebooks:
  - [nbs/08_utils_graphql.ipynb](nbs/08_utils_graphql.ipynb) - Added new methods
  - [nbs/08_utils_graphql_tests.ipynb](nbs/08_utils_graphql_tests.ipynb) - Added 6 new tests
  
- Generated code:
  - [fh_saas/utils_graphql.py](fh_saas/utils_graphql.py) - Auto-generated from notebook

- Exports:
  - `GraphQLClient` - Enhanced class with new methods
  - `execute_graphql` - New standalone function

## 🔗 Backward Compatibility

All existing code continues to work:
- ✅ `execute_query()` - Still available
- ✅ `execute_mutation()` - Still available
- ✅ `fetch_pages_generator()` - Still available for streaming
- ✅ Manual `AsyncAPIClient` usage - Still supported

The new methods are pure additions - no breaking changes!
