-- --------------------------------------------------------------------- --
-- 7. Videos: columna provider (dual-render json2video + local)           --
-- --------------------------------------------------------------------- --
-- Un guion puede generar DOS variantes de video que se persisten juntas
-- como 2 filas en `videos`, distinguidas por esta columna:
--   'json2video' → render generado por el motor cloud JSON2Video
--   'local'      → render generado por el microservicio local (MoviePy)
-- Backfill: las filas legacy se clasifican por su URL. Las filas del flujo
-- json2video persisten en MinIO con clave `json2video_*.mp4`, por lo que su
-- URL presignada contiene 'json2video'; el resto son renders locales.

ALTER TABLE videos ADD COLUMN IF NOT EXISTS provider VARCHAR(20);

UPDATE videos
   SET provider = CASE
       WHEN edited_video_uri LIKE '%json2video%' THEN 'json2video'
       ELSE 'local'
   END
 WHERE provider IS NULL;
