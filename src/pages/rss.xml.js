import rss from "@astrojs/rss";
import { getCollection } from "astro:content";

export async function GET(context) {
  const techniques = await getCollection("techniques");
  const items = techniques
    .map((t) => ({
      title: t.data.title,
      description: `${t.data.grade} — ${t.data.category}: ${(t.data.summary || "").substring(0, 200)}`,
      link: `/techniques/${t.data.slug || t.id.replace(/\.md$/, "")}/`,
      pubDate: new Date(t.data.last_searched || Date.now()),
    }))
    .sort((a, b) => b.pubDate - a.pubDate);

  return rss({
    title: "Focus Hacking — Research Digest",
    description: "Evidence-graded directory of free focus techniques. Updated weekly from PubMed.",
    site: context.site,
    items,
    customData: `<language>en-us</language>`,
  });
}
