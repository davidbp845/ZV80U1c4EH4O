import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const vault = defineCollection({
  loader: glob({ pattern: '**/*.md', base: '../vault_negocio' }),
  schema: z
    .object({
      categoria: z.string().optional(),
      tags: z.array(z.string()).optional(),
      publicar_web: z.boolean().default(false),
    })
    .passthrough(),
});

export const collections = { vault };
