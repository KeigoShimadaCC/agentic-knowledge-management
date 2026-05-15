import { test as base, expect, type APIRequestContext } from "@playwright/test";
import {
  addUserCookie,
  createTestUser,
  softDeleteAllObjects,
  type TestUser,
} from "./test-user";

type Fixtures = {
  testUser: TestUser;
  api: APIRequestContext;
};

export const test = base.extend<Fixtures>({
  testUser: async ({ context }, use) => {
    const user = await createTestUser();
    await addUserCookie(context, user.cookie);
    try {
      await use(user);
    } finally {
      await softDeleteAllObjects(user.api);
      await user.api.dispose();
    }
  },
  api: async ({ testUser }, use) => {
    await use(testUser.api);
  },
});

export { expect };
