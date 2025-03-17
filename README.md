# Keycloak and Permify Integration Guide

## 1. Keycloak Authentication Integration

### When integrating Keycloak into your application, the protect() middleware ensures that only authenticated users can access specific routes. 

Additionally, for multi-tenancy, the tenantId must be attached to the request to ensure data isolation between tenants.

### Keycloak's protect() Middleware

Keycloak's protect() middleware ensures that only authenticated users can access a route. It validates the JWT token included in the request headers and attaches the decoded token (containing user information) to the req object.

#### How It Works

- The client sends a request with a valid JWT token in the Authorization header.
- Keycloak's protect() middleware validates the token.
- If the token is valid, the request proceeds to the route handler.
- If the token is invalid or missing, the middleware returns a 401 Unauthorized response.

#### Example Integration

```typescript
import keycloak from '../config/keycloak';

// Protect a route
router.get('/protected-route', keycloak.protect(), (req, res) => {
  res.json({ message: 'You are authenticated!' });
});
```

## 2. Attaching tenantId to the Request

For multi-tenancy, the tenantId must be included in the request to ensure that users can only access data belonging to their tenant. This can be achieved in two ways:

### Option 1: Include tenantId in the Request Body or Query Parameters

The client includes the tenantId in the request body or query parameters.

Example:
```
// Request body
{
  "tenantId": "tenant-123"
}

// Query parameter
GET /api/contract-requests?tenantId=tenant-123
```

### Option 2: Extract tenantId from the JWT Token

Keycloak can include the tenantId in the JWT token when the user logs in.

The protect() middleware automatically decodes the token and attaches it to req.kauth.grant.access_token.content.

Example:

```typescript
router.get('/protected-route', keycloak.protect(), (req, res) => {
  const tenantId = req.kauth.grant.access_token.content.tenantId;
  res.json({ tenantId });
});
```

## 3. Enforcing Multi-Tenancy in Routes

Once the tenantId is available in the request, you can enforce multi-tenancy by:

1. Validating the tenantId in the request.
2. Using the tenantId to filter data in your database queries.

### Example: Enforcing Multi-Tenancy in contractRoutes.ts

```typescript
import express from 'express';
import keycloak from '../config/keycloak';
import { getContractRequests } from '../controllers/contractController';

const router = express.Router();

// Protect the route and enforce multi-tenancy
router.get('/', keycloak.protect(), (req, res, next) => {
  // Extract tenantId from the JWT token
  const tenantId = req.kauth.grant.access_token.content.tenantId;

  if (!tenantId) {
    return res.status(400).json({ message: 'Tenant ID is required' });
  }

  // Attach tenantId to the request object
  req.tenantId = tenantId;
  next();
}, getContractRequests);

export default router;
```

### Example: Using tenantId in the Controller

```typescript
export const getContractRequests = async (req: Request, res: Response) => {
  const { tenantId } = req; // Attached by the middleware

  try {
    const contractRequests = await prisma.contractRequest.findMany({
      where: { tenantId },
    });

    res.status(200).json({ data: contractRequests });
  } catch (error) {
    res.status(500).json({ message: 'Internal server error' });
  }
};
```

## 4. Keycloak Configuration

Ensure your Keycloak client is configured to include the tenantId in the JWT token. This can be done by:

1. Adding a custom attribute (e.g., tenantId) to the user in Keycloak.
2. Mapping the attribute to the token using a Mapper in the Keycloak client settings.

### Example Keycloak Mapper

- Name: tenantId
- Token Claim Name: tenantId
- Claim JSON Type: String
- User Attribute: tenantId

## 5. Authentication Summary

### Keycloak's protect() Middleware:

- Ensures only authenticated users can access protected routes.
- Decodes the JWT token and attaches user information to req.kauth.grant.access_token.content.

### Attaching tenantId:

- Include tenantId in the request body, query parameters, or JWT token.
- Extract tenantId from the token using req.kauth.grant.access_token.content.tenantId.

### Enforcing Multi-Tenancy:

- Validate the tenantId in the request.
- Use the tenantId to filter data in database queries.

### Keycloak Configuration:

- Add a custom tenantId attribute to users and map it to the JWT token.

### Example Workflow

#### Client Request:

```bash
GET /api/contract-requests
Authorization: Bearer <JWT_TOKEN>
```

#### Middleware:

- Keycloak validates the token and attaches the decoded payload to req.kauth.grant.access_token.content.
- Extract tenantId from the token and attach it to req.tenantId.

#### Controller:

- Use req.tenantId to filter contract requests for the tenant.

#### Response:

```json
{
  "data": [
    { "id": "contract-123", "tenantId": "tenant-123", "status": "PENDING" }
  ]
}
```

## 6. Permify Integration for Role-Based Access Control

### Entities

- **User**: Represents a user in the system.
- **Contract**: Represents a contract request.

### Relations

- **Tenant**: The tenant who owns the contract.
- **Vendor Manager**: Users with the VENDOR_MANAGER role.

### Actions

- **Approve**: Only VENDOR_MANAGER users can approve contracts.
- **Reject**: Only VENDOR_MANAGER users can reject contracts.
- **View**: Tenants can view their own contracts.

## 7. Setting Up Permify

### Step 1: Install Permify

Run the Permify server using Docker:

```bash
docker run -p 3478:3478 -p 3479:3479 ghcr.io/permify/permify serve
```

Verify that the server is running:

```bash
curl http://localhost:3478/health
```

### Step 2: Initialize Permify Client

In your config/permify.ts file, initialize the Permify client:

```typescript
import { PermifyClient } from '@permify/permify-node';

const permify = new PermifyClient({
  endpoint: 'http://localhost:3478', // Permify server URL
});

export default permify;
```

## 8. Defining Authorization Policies

### Policy YAML File

Create a policy.yaml file to define your authorization policies:

```yaml
# Define entities
entity user {}

entity contract {
  # Relations
  relation tenant @user               # The tenant who owns the contract
  relation vendor_manager @user       # Users with the "Vendor Manager" role

  # Actions
  action approve = vendor_manager     # Only vendor managers can approve
  action reject = vendor_manager      # Only vendor managers can reject
  action view = tenant                # Tenants can view their contracts
}
```

### Load the Policy

Use Permify's API to load the policy into the server:

```bash
curl -X POST http://localhost:3478/policies \
  -H "Content-Type: application/yaml" \
  --data-binary @policy.yaml
```

## 9. Integrating Permify into Your Application

### Step 1: Protect Routes with Keycloak

Use Keycloak's protect() middleware to ensure only authenticated users can access the route:

```typescript
import keycloak from '../config/keycloak';
router.patch('/approvals/business/:id', keycloak.protect(), approvalController.businessApproval);
```

### Step 2: Enforce Permify Policies

Use Permify to enforce authorization policies before allowing the action:

```typescript
import permify from '../config/permify';

router.patch(
  '/approvals/business/:id',
  keycloak.protect(),
  async (req, res, next) => {
    const { id: contractId } = req.params;
    const { id: userId, tenantId } = req.kauth.grant.access_token.content;

    // Check if the user is a Vendor Manager
    const isAllowed = await permify.checkPermission({
      subject: userId,
      resource: contractId,
      action: 'approve',
      context: { tenantId },
    });

    if (!isAllowed) {
      return res.status(403).json({ message: 'Forbidden: User is not a Vendor Manager' });
    }

    next();
  },
  approvalController.businessApproval
);
```

## 10. Enforcing RBAC in Routes and Controllers

### Example: Approval Controller

```typescript
import { Request, Response } from 'express';
import permify from '../config/permify';

export const businessApproval = async (req: Request, res: Response) => {
  const { id: contractId } = req.params;
  const { id: userId, tenantId } = req.kauth.grant.access_token.content;

  try {
    // Check if the user is authorized to approve the contract
    const isAllowed = await permify.checkPermission({
      subject: userId,
      resource: contractId,
      action: 'approve',
      context: { tenantId },
    });

    if (!isAllowed) {
      return res.status(403).json({ message: 'Forbidden: User is not a Vendor Manager' });
    }

    // Proceed with the approval logic
    // ...
  } catch (error) {
    res.status(500).json({ message: 'Internal server error' });
  }
};
```

## 11. Testing the Integration

### Step 1: Assign Roles

Use Permify's API to assign the vendor_manager role to a user:

```bash
curl -X POST http://localhost:3478/relations \
  -H "Content-Type: application/json" \
  -d '{
    "entity": "contract",
    "resource": "contract-456",
    "relation": "vendor_manager",
    "subject": "user-123"
  }'
```

### Step 2: Check Permissions

Use Permify's API to check if a user can approve a contract:

```bash
curl -X POST http://localhost:3478/permissions/check \
  -H "Content-Type: application/json" \
  -d '{
    "entity": "contract",
    "resource": "contract-456",
    "action": "approve",
    "subject": "user-123",
    "context": { "tenantId": "tenant-789" }
  }'
```

## 12. Example Workflow

### Client Request:

```bash
PATCH /api/approvals/business/contract-123
Authorization: Bearer <JWT_TOKEN>
```

### Keycloak Middleware:

- Validates the JWT token and attaches user information to req.kauth.grant.access_token.content.

### Permify Middleware:

- Checks if the user is authorized to approve the contract.
- Example: permify.checkPermission({ subject: userId, resource: contractId, action: 'approve' }).

### Controller:

- If authorized, proceeds with the approval logic.
- If not authorized, returns a 403 Forbidden response.

## 13. Summary

- Keycloak handles authentication and attaches user information to the request.
- Permify handles authorization by evaluating policies.
- The YAML policy ensures that only users with the VENDOR_MANAGER role can approve or reject contracts.
- The policy is enforced at both the authentication stage (via Keycloak) and the authorization stage (via Permify).
