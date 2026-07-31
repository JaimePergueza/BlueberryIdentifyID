import { useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiBlob } from "../lib/api";

interface ProtectedImageProps {
  endpoint: string;
  alt: string;
  caption: string;
}

export function ProtectedImage({ endpoint, alt, caption }: ProtectedImageProps) {
  const query = useQuery({
    queryKey: ["protected-image", endpoint],
    queryFn: () => apiBlob(endpoint),
    staleTime: 5 * 60_000,
  });
  const source = useMemo(
    () => (query.data ? URL.createObjectURL(query.data) : null),
    [query.data],
  );

  useEffect(
    () => () => {
      if (source) URL.revokeObjectURL(source);
    },
    [source],
  );

  return (
    <figure className="protected-image">
      <div className="protected-image-frame">
        {query.isLoading && <span className="spinner" aria-label={`Cargando ${caption}`} />}
        {query.isError && <span className="image-unavailable">Imagen no disponible</span>}
        {source && <img src={source} alt={alt} />}
      </div>
      <figcaption>{caption}</figcaption>
    </figure>
  );
}
