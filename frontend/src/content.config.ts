import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const vault = defineCollection({
  loader: glob({ pattern: '**/*.md', base: '../vault_negocio' }),
  schema: z
    .object({
      categoria: z.string().optional(),
      tags: z.array(z.string()).optional(),
      publicar_web: z.boolean().default(false),
      orden: z.number().optional(),
      // Texto corto para la tarjeta de la sección de contenido público;
      // el cuerpo completo de la nota se muestra al abrirla. Solo hace
      // falta si la nota se publica en la web.
      resumen: z.string().optional(),
    })
    .passthrough()
    .refine((data) => !data.publicar_web || Boolean(data.resumen?.trim()), {
      message: 'resumen es obligatorio cuando publicar_web es true',
      path: ['resumen'],
    }),
});

export const collections = { vault };
