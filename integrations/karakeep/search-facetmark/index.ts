// Auto-register the facetmark provider when this module is imported, matching
// packages/plugins/search-meilisearch/index.ts line for line.
//
// Registering is conditional on isConfigured(): with FACETMARK_URL or
// FACETMARK_TOKEN unset, nothing registers and karakeep keeps whatever Search
// provider was registered before this import. It does not fall back to an
// unauthenticated facetmark.
import { PluginManager, PluginType } from "@karakeep/shared/plugins";

import { FacetmarkProvider } from "./src";

if (FacetmarkProvider.isConfigured()) {
  PluginManager.register({
    type: PluginType.Search,
    name: "facetmark",
    provider: new FacetmarkProvider(),
  });
}
