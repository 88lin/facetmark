// Auto-register the facetmark provider when this package is imported, matching
// the shape of packages/plugins/search-meilisearch/index.ts exactly.
import { PluginManager, PluginType } from "@karakeep/shared/plugins";

import { FacetmarkProvider } from "./src";

if (FacetmarkProvider.isConfigured()) {
  PluginManager.register({
    type: PluginType.Search,
    name: "facetmark",
    provider: new FacetmarkProvider(),
  });
}
