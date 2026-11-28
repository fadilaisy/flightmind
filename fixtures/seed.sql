-- FlightMind fixture seed.
-- Owner: Role 2 (Koolkar), SCRUM-22. GENERATED: do not edit by hand. Regenerate with
--   python services/pipeline/scripts/make_seed.py
-- Source: fixtures/adsb_sample_500.pcap, decoded blocks from
-- fixtures/adsb_sample_500.decoded.jsonl, run through the pipeline's cleaning, track
-- split, detectors and compression. The local stack (SCRUM-31) loads this file as the
-- last init step (infra/docker-compose.yml, 02_seed.sql).
--
-- Cleaning: steps 1 to 5 only. The fragments step (fewer than 20 records per address) is skipped,
-- because on this 1.7 s sample it would set aside all 500 records and leave no telemetry.
--
-- Rows match contracts/schema.sql (v1.2): recording_files, telemetry, events, quarantine.
-- event_embeddings is left empty (needs the embedding API, Role 3). Every telemetry row
-- that an event's raw_refs points at is present. The whole file is one transaction and
-- every INSERT is ON CONFLICT DO NOTHING, so loading it twice changes nothing.
--
-- Counts: 500 packets, 500 decoded points, 382 telemetry rows, 1 quarantine rows, 0 events.
-- The detectors found no events on this 500-packet sample, so the events table gets no rows.

BEGIN;

INSERT INTO recording_files (id, uri, sha256, size_bytes, record_count, first_ts, last_ts)
VALUES ('adsb_sample_500', 'fixtures/adsb_sample_500.pcap', '5f9b6d8b6e2875c416719d24a224067f99b9b47a8cc14268273d59add2f84faf', 55508, 500, '2024-12-30T04:49:56.047749+00:00', '2024-12-30T04:49:57.814877+00:00')
ON CONFLICT DO NOTHING;

INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.047749+00:00', '76cc67', 'SIA528', 3.7360382, 99.1625547, 37975, 40600, 517.45608, 281.3543701, 0, '0123', NULL, 50, 201, NULL, 'adsb_sample_500:1', 24, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.048393+00:00', '8a03c7', NULL, -7.9007363, 110.0580955, 75, 125, 0.0, 180.0, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:2', 137, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.057941+00:00', '8a02d4', 'GIA193', -0.9973741, 103.4493256, 37000, 39650, 445.16591999999997, 140.9161377, 62, NULL, false, 50, 201, NULL, 'adsb_sample_500:3', 240, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.057942+00:00', '8a09b8', 'AWQ211', 0.4522634, 104.1102862, 35000, 37575, 464.06232, 134.7363281, 62, '2161', NULL, 50, 201, NULL, 'adsb_sample_500:4', 349, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.068806+00:00', 'b1b173', NULL, 0.9200191, 104.519999, NULL, NULL, NULL, NULL, NULL, NULL, false, 50, 201, NULL, 'adsb_sample_500:5', 462, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.088938+00:00', '76b86d', 'TGW539', 1.1879826, 104.1045356, 5250, 5575, 240.60060000000001, 230.559082, -1025, '5572', NULL, 50, 201, NULL, 'adsb_sample_500:6', 555, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.099263+00:00', '7c8064', 'QFA255', 1.3447523, 103.9756608, 200, 225, 149.8536, 23.1481934, -894, '1370', NULL, 50, 201, NULL, 'adsb_sample_500:7', 668, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.099264+00:00', '76d1cd', 'TGW247', 1.1463547, 104.2176819, 8175, 8650, 249.38964, 265.4077148, -319, '6661', NULL, 50, 201, NULL, 'adsb_sample_500:8', 782, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.099311+00:00', '8851e7', 'THA401', 1.2018657, 103.9158154, 2550, 2675, 192.70008, 20.3137207, -125, '0746', NULL, 50, 201, NULL, 'adsb_sample_500:9', 895, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.099312+00:00', '8a0ab8', 'TNU679', 2.2606301, 102.6885009, 22450, 23950, 382.76352, 316.8017578, -381, '2436', NULL, 50, 201, NULL, 'adsb_sample_500:10', 1009, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.109230+00:00', '76b44f', 'SIA995', 2.3963714, 100.5625391, 28675, 30675, 435.05856, 130.2429199, 894, '6730', NULL, 50, 201, NULL, 'adsb_sample_500:11', 1122, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.109231+00:00', '8a07b7', 'AWQ327', 1.0089612, 103.5320878, 31025, 33300, 462.74399999999997, 133.0718994, 125, NULL, false, 50, 201, NULL, 'adsb_sample_500:12', 1235, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.109232+00:00', '8a099f', 'BTK7265', 3.4272838, 100.6127071, 22025, 23500, 392.43168000000003, 265.0286865, 0, '2124', NULL, 50, 201, NULL, 'adsb_sample_500:13', 1344, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.109282+00:00', '885ca8', 'MJJ821', 3.7659287, 103.1003165, 38000, 40750, 482.95908000000003, 333.1713867, 0, '2265', false, 50, 201, NULL, 'adsb_sample_500:14', 1457, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.109283+00:00', '801698', 'AXB629', 1.7116356, 100.5394506, 37975, 40600, 472.85172000000006, 292.1154785, 0, '0170', NULL, 50, 201, NULL, 'adsb_sample_500:15', 1569, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.109322+00:00', '8832a8', 'TLM105', 2.4644566, 103.8368511, 25700, 27425, 447.58296, 335.4400635, 1531, NULL, false, 50, 201, NULL, 'adsb_sample_500:16', 1682, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.109322+00:00', '8a0aa0', 'MYU9903', 0.4954362, 104.6358275, 25175, 26825, 405.83484, 163.394165, 2050, '2206', NULL, 50, 201, NULL, 'adsb_sample_500:17', 1791, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.109349+00:00', '750459', 'AXM5749', 2.7982092, 102.6682663, 21000, 22350, 393.75, 245.0610352, -3262, '0430', NULL, 50, 201, NULL, 'adsb_sample_500:18', 1904, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.109380+00:00', '75031a', 'MAS610', 2.3106909, 102.940414, 24000, 25625, 383.64264000000003, 243.3691406, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:19', 2017, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.109381+00:00', '8a03f3', 'AWQ247', 2.2318339, 102.2626519, 35000, 37525, 433.30068, 139.4000244, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:20', 2126, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.109419+00:00', '76b865', 'TGW740', 3.3312821, 100.5517673, 34000, 36425, 485.81532000000004, 284.666748, 0, '2252', NULL, 50, 201, NULL, 'adsb_sample_500:21', 2235, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.109794+00:00', '06a117', 'QTR963', 3.332119, 95.8719134, 38000, 40475, 511.96284, 266.3031006, 0, '4115', false, 50, 201, NULL, 'adsb_sample_500:22', 2348, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.119268+00:00', '76b44a', 'SIA534', 4.6149874, 94.5600772, 36000, 38375, 480.10248, 281.7773438, 0, '2212', false, 50, 201, NULL, 'adsb_sample_500:23', 2462, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.119269+00:00', 'ac954d', 'N91LA', 6.5820765, 99.1326642, 38000, 40650, 522.7293599999999, 290.3741455, 0, '2223', false, 50, 201, NULL, 'adsb_sample_500:24', 2576, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.119270+00:00', '76d1c7', 'TGW732', 3.502686, 95.9149575, 34025, 36325, 482.95908000000003, 266.3195801, 0, '2201', false, 50, 201, NULL, 'adsb_sample_500:25', 2690, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.119322+00:00', '780cb9', 'CCA977', 0.8130312, 106.8604088, 37000, 39700, 470.87388000000004, 169.8596191, 0, '0072', NULL, 50, 201, NULL, 'adsb_sample_500:26', 2804, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.119323+00:00', '7505a3', 'MAS487', 2.4132371, 99.8200178, 30175, 32250, 489.11148, 279.7723389, 706, '2140', NULL, 50, 201, NULL, 'adsb_sample_500:28', 3030, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.119323+00:00', '78212c', 'CSN365', 3.1452012, 101.8879151, 16125, 17175, 368.9208, 183.883667, -769, '3104', NULL, 50, 201, NULL, 'adsb_sample_500:27', 2917, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.120018+00:00', '76cd76', 'SIA221', 1.3742566, 104.3085766, 8800, 9275, 365.18544, 114.7412109, 1600, '2215', NULL, 50, 201, NULL, 'adsb_sample_500:29', 3143, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.129476+00:00', '76cc6d', 'SIA929', 1.1703658, 104.7437596, 14975, 16000, 384.74136, 267.9180908, -1919, '7007', NULL, 50, 201, NULL, 'adsb_sample_500:30', 3256, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.129477+00:00', '750324', 'AXM6047', 2.053349, 102.6134205, 18225, 19525, 387.81756, 282.9638672, -1531, NULL, NULL, 50, 201, NULL, 'adsb_sample_500:31', 3369, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.129478+00:00', '896121', 'UAE369', 2.295177, 102.8957176, 32000, 34300, 511.30368000000004, 286.237793, 0, '4127', NULL, 50, 201, NULL, 'adsb_sample_500:32', 3480, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.129478+00:00', '8a074d', 'CTV882', -1.1371279, 102.5220966, 34000, 36475, 454.17492000000004, 316.7852783, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:33', 3593, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.129479+00:00', '750281', 'MAS2585', 2.8785038, 102.4889445, 18300, 19500, 380.56644, 235.6018066, -2556, NULL, false, 50, 201, NULL, 'adsb_sample_500:34', 3702, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.129533+00:00', '8963e6', 'UAE355', 3.391664, 100.9649134, 38000, 40600, 503.3934, 289.9841309, 0, '0166', NULL, 50, 201, NULL, 'adsb_sample_500:35', 3811, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.129841+00:00', '7820fb', 'CHH702', -0.6578493, 104.233861, 30000, 32200, 452.8566, 349.3103027, 0, '2426', NULL, 50, 201, NULL, 'adsb_sample_500:36', 3924, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.142867+00:00', '8a02ff', 'CTV171', -5.9642029, 109.2025137, 34000, 36425, 457.47072, 270.1263428, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:37', 4037, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.142917+00:00', '75020f', NULL, 3.0310893, 104.6388102, 38000, 40700, 468.01764000000003, 276.5039062, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:38', 4146, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.143303+00:00', '8a08e9', 'SJV171', 0.3312421, 101.2050247, 34025, 36450, 470.43467999999996, 311.3800049, 62, '1736', NULL, 50, 201, NULL, 'adsb_sample_500:39', 4249, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.143403+00:00', '8852e4', 'THA482', 3.8919926, 103.2519364, 39975, 42750, 499.87800000000004, 336.6650391, 0, '1463', NULL, 50, 201, NULL, 'adsb_sample_500:40', 4362, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.143621+00:00', '76cce1', NULL, 4.3820429, 100.9260535, 41000, 43625, 461.42568, 141.8609619, 0, NULL, NULL, 50, 201, NULL, 'adsb_sample_500:41', 4475, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.144220+00:00', '76cc6a', 'SIA945', 0.8390594, 105.1710892, 22975, 24575, 439.89264000000003, 312.0556641, -1919, '4122', NULL, 50, 201, NULL, 'adsb_sample_500:42', 4579, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.155220+00:00', '76b441', 'SIA948', -0.0455117, 105.5358911, 30300, 32500, 441.21096, 119.8718262, 831, '2245', NULL, 50, 201, NULL, 'adsb_sample_500:43', 4692, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.162716+00:00', '76b453', 'SIA921', 2.0309687, 106.659286, 36000, 38600, 468.8964, 232.6190186, 0, '6512', NULL, 50, 201, NULL, 'adsb_sample_500:44', 4805, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.171864+00:00', '76d256', 'TGW279', -2.8916574, 104.7318292, 35975, 38600, 458.34947999999997, 347.4151611, -62, NULL, false, 50, 201, NULL, 'adsb_sample_500:45', 4918, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.171865+00:00', '7502ad', 'AXM1730', 1.4962435, 104.0492392, 6800, 7125, 267.18768, 356.786499, 3581, NULL, false, 50, 201, NULL, 'adsb_sample_500:47', 5140, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.171865+00:00', '76cc75', 'SIA601', 1.2846494, 103.9502764, 1400, 1475, 157.10436, 22.8186035, -894, '7105', NULL, 50, 201, NULL, 'adsb_sample_500:46', 5027, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.171866+00:00', '7503ab', NULL, 8.4388518, 100.5628824, 37000, NULL, NULL, NULL, NULL, NULL, false, 50, 201, NULL, 'adsb_sample_500:48', 5249, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.171866+00:00', '885315', 'THA268', 8.3105564, 100.3581119, 28000, 29975, 448.02252, 1.2799072, 1150, NULL, false, 50, 201, NULL, 'adsb_sample_500:49', 5344, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.172401+00:00', '885302', 'THA440', 4.2660427, 105.1852942, 33975, 36450, 486.91404000000006, 333.4350586, -62, NULL, false, 50, 201, NULL, 'adsb_sample_500:50', 5453, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.182008+00:00', '76cd17', 'SIA157', 2.8978801, 104.5225525, 29400, 31500, 406.93356, 226.5930176, -3325, '1635', NULL, 50, 201, NULL, 'adsb_sample_500:51', 5562, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.182009+00:00', '75021f', 'MAS2532', 2.778511, 105.5995989, 35000, 37525, 434.1798, 103.8427734, -62, NULL, false, 50, 201, NULL, 'adsb_sample_500:52', 5675, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.182010+00:00', '76cd11', 'SIA438', 3.2496142, 96.0812545, 40000, 42525, 508.66704, 267.2973633, 0, '0103', false, 50, 201, NULL, 'adsb_sample_500:54', 5893, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.182171+00:00', '896112', 'UAE358', -2.1815157, 103.7384892, 35000, 37525, 479.00376, 127.2052002, 0, '1737', NULL, 50, 201, NULL, 'adsb_sample_500:55', 6007, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.203060+00:00', '86e058', 'TZP61', 4.2485976, 106.090765, 40000, 42775, 503.17379999999997, 251.9604492, 62, '3620', NULL, 50, 201, NULL, 'adsb_sample_500:56', 6120, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.212671+00:00', '7c492a', 'QFA1', 0.9513903, 105.3941202, 24700, 26450, 395.06831999999997, 307.9138184, -575, '1334', NULL, 50, 201, NULL, 'adsb_sample_500:57', 6233, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.239847+00:00', '8a0454', 'LNI316', -3.4958625, 114.5670176, 3575, 3925, 189.84384, 16.5234375, -194, '6331', false, 50, 201, NULL, 'adsb_sample_500:58', 6346, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.243446+00:00', '8a1812', 'LNI6001', -4.1757274, 114.5734763, 14875, 15925, 350.90315999999996, 350.4858398, -1150, '4405', false, 50, 201, NULL, 'adsb_sample_500:59', 6460, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.243447+00:00', '8a0827', 'BTK6231', -5.6560493, 113.0726194, 36000, 38575, 471.31343999999996, 263.1774902, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:60', 6573, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.243448+00:00', '4bb10b', 'THY067', -4.4516087, 112.6744294, 34000, 36450, 515.9178, 330.2545166, 0, '4141', false, 50, 201, NULL, 'adsb_sample_500:61', 6682, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.243500+00:00', '888158', 'VJC92', -1.1682415, 114.8622108, 35000, 37550, 455.05368000000004, 359.8736572, 62, '1501', false, 50, 201, NULL, 'adsb_sample_500:62', 6796, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.243501+00:00', '7823c8', 'CSN8137', -5.3758335, 114.1930103, 31950, 34375, 448.02252, 198.4735107, 194, '3133', false, 50, 201, NULL, 'adsb_sample_500:63', 6910, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.243538+00:00', '8a08de', 'SJV664', -4.3392777, 114.0577412, 23225, 24950, 310.69331999999997, 52.0587158, -1856, NULL, false, 50, 201, NULL, 'adsb_sample_500:64', 7024, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.243538+00:00', '8a1843', 'BJMASI B', -3.4418535, 114.7460175, NULL, 225, NULL, NULL, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:65', 7133, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.243565+00:00', '896713', 'ETD425', 8.0743504, 97.5187469, 28200, 30100, 466.04016, 269.3847656, 769, '6160', false, 50, 201, NULL, 'adsb_sample_500:66', 7233, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.274064+00:00', '885105', 'THA410', 6.493156, 102.2510648, 43000, 45600, 493.06644, 346.272583, 0, '0120', NULL, 50, 201, NULL, 'adsb_sample_500:68', 7460, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.274108+00:00', '76b869', 'TGW784', 4.5849252, 99.4312048, 34050, 36500, 478.56456000000003, 310.847168, 0, '0152', NULL, 50, 201, NULL, 'adsb_sample_500:69', 7573, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.274109+00:00', '8a1829', 'MEDAN', 3.6417103, 98.8853002, NULL, NULL, NULL, NULL, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:70', 7686, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.274144+00:00', '7500dd', 'AXM889', 5.9660268, 102.1714139, 36975, 39600, 431.76276, 161.7736816, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:71', 7786, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.274180+00:00', '750453', 'AXM13', 3.1294084, 101.1967421, 15850, 16800, 368.04204, 317.6422119, 2369, '2112', NULL, 50, 201, NULL, 'adsb_sample_500:72', 7895, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.274207+00:00', '750441', 'AXM53', 4.4569731, 98.358686, 34000, 36350, 476.58708, 298.4490967, 0, '2173', NULL, 50, 201, NULL, 'adsb_sample_500:73', 8008, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.274241+00:00', '8a09e4', 'PAS307', 3.182559, 99.2679977, 16250, 17275, 369.79992, 134.6704102, 1794, '4751', NULL, 50, 201, NULL, 'adsb_sample_500:74', 8121, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.274274+00:00', '8850af', 'THA436', 6.467278, 102.2186422, 40050, 42775, 477.9054, 339.9334717, -62, NULL, false, 50, 201, NULL, 'adsb_sample_500:75', 8234, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.274306+00:00', '750458', 'AXM65', 4.7612858, 101.0133219, 31225, 33400, 466.25976, 336.6265869, 575, '2113', NULL, 50, 201, NULL, 'adsb_sample_500:76', 8343, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.274306+00:00', '8a07a7', 'MYU219', 3.6138582, 98.7956285, 5000, 5125, 247.63176, 308.4411621, 3394, '6720', NULL, 50, 201, NULL, 'adsb_sample_500:77', 8456, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.274343+00:00', '750042', 'FFM1441', 4.1469741, 101.0331702, 13000, NULL, NULL, NULL, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:78', 8569, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.274343+00:00', '77044c', 'ALK309', 2.727313, 96.3036847, 36000, 38400, 473.95007999999996, 290.1159668, 0, '0161', NULL, 50, 201, NULL, 'adsb_sample_500:79', 8678, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.274378+00:00', '76b448', 'SIA739', 4.7377682, 100.8451796, 37000, 39575, 439.23348, 141.5643311, 0, '0764', NULL, 50, 201, NULL, 'adsb_sample_500:80', 8791, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.274445+00:00', '750287', 'AXM6327', 3.8616085, 100.7591772, 28900, 31025, 451.97748, 155.4180908, -831, NULL, false, 50, 201, NULL, 'adsb_sample_500:83', 9130, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.274445+00:00', 'a0105b', 'FDX6020', 3.7697268, 101.4321113, 17125, 18150, 428.90616, 349.6618652, 1981, '2167', NULL, 50, 201, NULL, 'adsb_sample_500:84', 9239, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.274480+00:00', '70e08d', 'KTC168', 3.684926, 101.7708635, 20175, 21425, 380.56644, 29.2565918, 1406, NULL, false, 50, 201, NULL, 'adsb_sample_500:85', 9352, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.274481+00:00', '75010b', 'AXM103', 4.3997025, 101.1716366, 28175, 30150, 442.30967999999996, 335.9838867, 762, NULL, false, 50, 201, NULL, 'adsb_sample_500:86', 9461, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.284953+00:00', '8a09ca', 'PAS113', -5.9633875, 108.9095736, 36000, 38625, 446.48424, 270.1263428, 0, '4420', NULL, 50, 201, NULL, 'adsb_sample_500:87', 9570, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.294229+00:00', '8a061e', 'CTV684', -7.6506686, 112.9983115, 34950, 37500, 445.60548, 112.5384521, -62, NULL, false, 50, 201, NULL, 'adsb_sample_500:88', 9683, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.294230+00:00', '8a09f8', 'TNU5110', -6.7058444, 110.0303936, 39000, 41775, 451.97748, 101.7333984, 62, '2334', NULL, 50, 201, NULL, 'adsb_sample_500:89', 9792, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.294766+00:00', '8a08f8', NULL, -7.9000068, 110.0660133, NULL, NULL, NULL, NULL, NULL, NULL, false, 50, 201, NULL, 'adsb_sample_500:90', 9905, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.304683+00:00', '75059c', 'MAS724', 0.6234741, 103.9816904, 38000, 40675, 453.07620000000003, 348.1677246, 0, '2425', NULL, 50, 201, NULL, 'adsb_sample_500:91', 9998, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.304684+00:00', '76cccd', 'SIA7822', 1.3858223, 104.0077615, 2350, 2425, NULL, NULL, 894, '0121', NULL, 50, 201, NULL, 'adsb_sample_500:92', 10111, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.304685+00:00', '8a0574', 'LNI664', -7.2870469, 110.9676003, 24900, 26650, 417.48048, 44.1265869, 450, '4650', NULL, 50, 201, NULL, 'adsb_sample_500:93', 10220, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.304685+00:00', '8a0942', 'MYU6012', 0.8905363, 103.9254069, 40000, 42700, 432.20232, 347.8601074, 0, '2331', NULL, 50, 201, NULL, 'adsb_sample_500:94', 10333, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.304965+00:00', '76cc64', 'SIA621', 1.1435652, 103.9889216, 4850, 5150, 216.65052, 270.5273438, -962, '3622', NULL, 50, 201, NULL, 'adsb_sample_500:95', 10446, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.314696+00:00', '780171', 'CPA725', 3.8328552, 103.5746384, 36000, 38575, 499.43843999999996, 263.6828613, -125, NULL, false, 50, 201, NULL, 'adsb_sample_500:96', 10559, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.314697+00:00', '758384', 'PAL502', 2.2771096, 106.4816165, 30875, 33100, 467.13852, 37.7050781, 769, '2262', NULL, 50, 201, NULL, 'adsb_sample_500:97', 10668, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.314925+00:00', '76cd07', 'SIA510', 4.8547339, 93.4070277, 40000, 42475, 508.88664, 281.9036865, 0, '2222', false, 50, 201, NULL, 'adsb_sample_500:98', 10782, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.324774+00:00', '75027d', 'AXM379', -0.6178522, 106.5845704, 38000, 40650, 457.25111999999996, 308.973999, -62, NULL, false, 50, 201, NULL, 'adsb_sample_500:99', 10896, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.364476+00:00', '7c146a', 'QFA36', -10.7893467, 110.8864903, 37000, 39600, 487.5732, 156.3244629, 62, '0102', NULL, 50, 201, NULL, 'adsb_sample_500:100', 11005, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.367340+00:00', '8a08fb', NULL, 1.3800073, 97.4070168, NULL, NULL, NULL, NULL, NULL, NULL, false, 50, 201, NULL, 'adsb_sample_500:101', 11118, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.376351+00:00', '750441', 'AXM53', 4.4564152, 98.359673, 34000, 36350, 475.92755999999997, 298.4490967, 0, '2173', NULL, 50, 201, NULL, 'adsb_sample_500:102', 11211, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.396216+00:00', '8003b3', 'AXB660', 3.9436841, 95.9699965, 35000, 37275, 453.95496, 107.0397949, 0, '0662', false, 50, 201, NULL, 'adsb_sample_500:103', 11324, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.416632+00:00', '76cd0f', 'SIA633', 2.535975, 107.3195601, 40000, 42750, 511.08408000000003, 232.8607178, 0, '3220', NULL, 50, 201, NULL, 'adsb_sample_500:105', 11547, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.416674+00:00', '8a03ab', 'CTV667', -5.9619713, 107.4839044, 12050, 12875, 306.95796, 270.1867676, -1344, NULL, false, 50, 201, NULL, 'adsb_sample_500:106', 11660, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.416716+00:00', '78143a', 'CXA8683', -5.7946873, 106.9046974, 5950, 6350, 261.91404, 167.8765869, -831, '6240', false, 50, 201, NULL, 'adsb_sample_500:107', 11769, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.416786+00:00', '8a074b', 'CTV955', -3.8092303, 105.5584216, 32975, 35375, 462.96396, 141.0479736, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:108', 11883, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.416818+00:00', '8a193d', 'F03', -6.1265087, 106.6441798, NULL, NULL, 0.0, 0.0, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:109', 11992, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.416876+00:00', '7c4928', 'QFA82', -3.570106, 109.8892665, 39000, 41725, 485.37611999999996, 128.4741211, 0, '2243', false, 50, 201, NULL, 'adsb_sample_500:110', 12095, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.416912+00:00', '750597', 'MAS251', -3.2759857, 106.5830684, 37000, 39675, 477.46584, 150.1062012, 0, '2376', false, 50, 201, NULL, 'adsb_sample_500:111', 12209, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.416946+00:00', '8a09c2', 'TNU5106', -6.1108661, 106.6691351, NULL, NULL, 10.10736, 67.5, NULL, '2421', true, 50, 201, NULL, 'adsb_sample_500:112', 12323, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.416978+00:00', '7c6bbd', 'JST8', -4.0536332, 107.5008559, 38975, 41750, 488.01275999999996, 153.0670166, 62, '0151', false, 50, 201, NULL, 'adsb_sample_500:113', 12429, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.417009+00:00', '76cda5', 'SIA967', -3.693316, 105.1924396, 39500, 42225, 488.23235999999997, 342.6031494, 1150, '2414', false, 50, 201, NULL, 'adsb_sample_500:114', 12543, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.417010+00:00', '8a047a', NULL, -6.1158442, 106.662848, NULL, NULL, 0.0, 337.5, NULL, '2000', true, 50, 201, NULL, 'adsb_sample_500:115', 12657, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.417045+00:00', '500567', 'T7JRG', -6.2358999, 106.9579768, 1325, 1425, 147.65616, 245.1708984, -894, '5035', false, 50, 201, NULL, 'adsb_sample_500:117', 12856, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.417045+00:00', '8a193e', 'F08', -6.1076474, 106.6568613, NULL, NULL, NULL, NULL, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:116', 12757, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.417080+00:00', '8a04e4', 'BTK7162', -4.2254877, 106.3613033, 34000, 36450, 462.74399999999997, 157.6483154, -894, '5471', false, 50, 201, NULL, 'adsb_sample_500:119', 13084, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.417080+00:00', '8a093b', 'BTK6887', -6.0883784, 106.7083597, 925, 975, 140.40540000000001, 247.8186035, -706, '4763', false, 50, 201, NULL, 'adsb_sample_500:118', 12970, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.417115+00:00', '8a0a95', 'PKADL', -6.1358428, 106.6568828, NULL, NULL, 12.08484, 329.0625, NULL, '5046', true, 50, 201, NULL, 'adsb_sample_500:120', 13198, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.417116+00:00', '8a1952', 'AMC02', -6.1244059, 106.6500378, NULL, NULL, NULL, NULL, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:121', 13306, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.417150+00:00', '8a06d0', 'CTV986', -4.3387628, 105.4526138, 26000, 27850, 413.74512, 332.8143311, 62, NULL, false, 50, 201, NULL, 'adsb_sample_500:122', 13405, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.417151+00:00', '750517', 'AXM354', -5.6437325, 106.2549162, 17325, 18475, 380.34684000000004, 327.5628662, 1150, '2312', false, 50, 201, NULL, 'adsb_sample_500:123', 13514, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.417187+00:00', '8a044e', 'GIA324', -6.5113306, 109.4692111, 33000, 35325, 442.08972, 104.0020752, 62, NULL, false, 50, 201, NULL, 'adsb_sample_500:124', 13628, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.417187+00:00', '8a04a4', 'CTV216', -6.3781214, 107.1802139, 16875, 18000, 386.05967999999996, 103.1726074, 1662, NULL, false, 50, 201, NULL, 'adsb_sample_500:125', 13737, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.417222+00:00', '780acf', 'CCA475', -6.0247993, 106.8386722, 3225, 3450, 187.6464, 222.62146, -831, '1527', false, 50, 201, NULL, 'adsb_sample_500:127', 13960, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.417222+00:00', '8a0604', 'BTK6269', -6.030035, 106.9258761, 4975, 5325, 206.1036, 248.6645508, -769, '5020', false, 50, 201, NULL, 'adsb_sample_500:126', 13846, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.417258+00:00', '8a02d5', 'GIA415', -5.9633017, 108.5010195, 30100, 32275, 424.9512, 270.1373291, -2112, NULL, false, 50, 201, NULL, 'adsb_sample_500:128', 14074, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.417292+00:00', '8a0376', NULL, -6.1214018, 106.6451454, NULL, NULL, 10.98648, 247.5, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:130', 14283, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.417293+00:00', '8a193f', 'F09', -6.1188698, 106.654458, NULL, NULL, NULL, NULL, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:131', 14379, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.417328+00:00', '8a0838', 'LNI383', -6.1194277, 106.7014503, 650, 700, 154.46772, 248.7469482, -769, '4714', false, 50, 201, NULL, 'adsb_sample_500:132', 14478, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.417328+00:00', '8a1915', 'AMC T1F', -6.1313581, 106.6506815, NULL, NULL, 12.96396, 81.5625, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:133', 14592, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.417392+00:00', '7502d9', 'MXD172', -0.4205489, 105.9008646, 36000, 38625, 452.19744000000003, 323.7121582, 62, '4123', NULL, 50, 201, NULL, 'adsb_sample_500:135', 14808, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.426634+00:00', '8a07b7', 'AWQ327', 1.0097766, 103.531208, 31000, 33275, 462.08484, 133.0718994, 125, NULL, false, 50, 201, NULL, 'adsb_sample_500:136', 14921, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.429521+00:00', '7504ec', 'AXM5195', 3.6146522, 106.1120081, 34000, 36525, 481.42080000000004, 270.4779053, -62, '0466', NULL, 50, 201, NULL, 'adsb_sample_500:137', 15030, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.446987+00:00', '75020f', NULL, 3.0313683, 104.6362567, 38000, 40700, 467.35847999999993, 276.5039062, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:140', 15369, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.497796+00:00', '8832a8', 'TLM105', 2.4652076, 103.8365293, 25725, 27475, 446.9238, 335.4400635, 1538, NULL, false, 50, 201, NULL, 'adsb_sample_500:147', 16118, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.497839+00:00', 'b2b177', NULL, 2.4100184, 96.3300133, NULL, NULL, NULL, NULL, NULL, NULL, false, 50, 201, NULL, 'adsb_sample_500:148', 16227, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.498566+00:00', '76cd02', 'SIA235', 0.7648802, 104.5576787, 14150, 15050, 377.49024000000003, 164.3444824, 831, '0126', NULL, 50, 201, NULL, 'adsb_sample_500:149', 16320, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.528519+00:00', '76cd0d', 'SIA516', 7.5568128, 98.9046121, 40000, 42575, 515.6982, 313.192749, 0, '2261', false, 50, 201, NULL, 'adsb_sample_500:150', 16433, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.538599+00:00', '75054c', 'MAS160', 4.4719076, 95.5414224, 32000, 34075, 523.60848, 281.0083008, 0, '2135', false, 50, 201, NULL, 'adsb_sample_500:151', 16547, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.538600+00:00', '76b86b', 'TGW653', 6.5424442, 99.5894122, 32550, 34850, 459.6678, 138.0871582, 1025, '6150', false, 50, 201, NULL, 'adsb_sample_500:153', 16775, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.538600+00:00', '8017f2', 'IGO1512', 5.7429314, 96.184938, 36000, 38400, 483.61824, 290.8355713, 0, '4116', false, 50, 201, NULL, 'adsb_sample_500:152', 16661, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.538601+00:00', '06a138', 'QTR847', 8.0008793, 95.3413081, 34000, 36250, 507.12876, 268.7585449, 0, '0752', false, 50, 201, NULL, 'adsb_sample_500:154', 16889, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.538601+00:00', '76cd15', 'SIA522', 4.6949387, 94.3219399, 34000, 36200, 520.75188, 281.0742188, 0, '2263', false, 50, 201, NULL, 'adsb_sample_500:155', 17003, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.538665+00:00', '896327', 'ETD477', 5.4435539, 94.7480035, 32000, 34125, 513.50112, 288.5064697, 0, '4114', false, 50, 201, NULL, 'adsb_sample_500:156', 17117, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.569934+00:00', '782472', 'CQH7199', -2.4156618, 107.7385426, 33000, 35425, 433.95984, 165.9979248, 62, '3124', NULL, 50, 201, NULL, 'adsb_sample_500:159', 17458, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.579438+00:00', '76cda5', 'SIA967', -3.6919212, 105.1919675, 39525, 42250, 488.23235999999997, 342.6031494, 1150, '2414', NULL, 50, 201, NULL, 'adsb_sample_500:161', 17684, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.579489+00:00', '8a03c8', 'GIA839', -2.1777177, 106.1409116, 35000, 37450, 437.47560000000004, 160.3619385, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:163', 17910, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.579919+00:00', '8a0508', 'CTV983', -2.8926873, 104.6866822, NULL, NULL, NULL, NULL, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:165', 18132, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.579994+00:00', '8a0a1e', 'BTK6884', -2.7590489, 103.6362648, 34000, 36475, 467.35847999999993, 317.9498291, 62, '2540', NULL, 50, 201, NULL, 'adsb_sample_500:167', 18340, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.579994+00:00', 'ddeeff', 'PALEMB', -2.9002833, 104.7000074, NULL, NULL, NULL, NULL, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:168', 18453, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.580027+00:00', '8a082a', 'LNI257', -2.4787688, 103.7061095, 33000, 35375, 457.03116000000006, 116.2298584, 0, '6254', NULL, 50, 201, NULL, 'adsb_sample_500:169', 18553, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.580059+00:00', '76cc6b', 'SIA276', -1.7725539, 107.9312754, 38000, 40725, 500.53716, 320.2679443, -62, '1546', NULL, 50, 201, NULL, 'adsb_sample_500:170', 18666, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.580059+00:00', '8a03aa', 'CTV887', -2.7817297, 104.8947144, 37025, 39650, 447.80256, 140.8007812, 62, NULL, false, 50, 201, NULL, 'adsb_sample_500:171', 18779, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.580158+00:00', '750599', 'MAS145', -0.7583356, 106.2339735, 37000, 39650, 463.18356, 144.0472412, 62, '2165', NULL, 50, 201, NULL, 'adsb_sample_500:174', 19110, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.580195+00:00', '8a0a67', 'TNU698', -3.3030868, 106.0155129, 32975, 35375, 443.18844, 158.7030029, 0, '2546', NULL, 50, 201, NULL, 'adsb_sample_500:175', 19223, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.580229+00:00', '750594', 'MAS147', -3.1359959, 106.1545157, 35000, 37550, 479.66292, 155.6268311, 0, '2152', NULL, 50, 201, NULL, 'adsb_sample_500:176', 19336, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.580405+00:00', '76cd03', 'SIA204', 0.079329, 107.4391437, 43000, 45700, 485.59572, 303.4918213, 0, '1145', NULL, 50, 201, NULL, 'adsb_sample_500:177', 19449, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.600233+00:00', '76cdb0', 'SIA895', 2.5490642, 104.1504335, 21325, 22725, 373.75488, 227.0544434, -575, '5176', NULL, 50, 201, NULL, 'adsb_sample_500:181', 19901, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.600234+00:00', '750424', 'MXD171', -0.0843501, 105.851469, 35000, 37575, 460.76652000000007, 128.3093262, 0, '2127', NULL, 50, 201, NULL, 'adsb_sample_500:182', 20014, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.600234+00:00', '8a09c4', 'SJV201', -6.9867682, 112.1401978, 17800, 19025, NULL, NULL, NULL, '6305', NULL, 50, 201, NULL, 'adsb_sample_500:183', 20127, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.601290+00:00', '750324', 'AXM6047', 2.0535207, 102.6124978, 18200, 19475, 387.37800000000004, 282.9638672, -1538, '0335', NULL, 50, 201, NULL, 'adsb_sample_500:184', 20234, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.620937+00:00', '7801b4', 'CPA797', 2.2515106, 106.8138242, 39000, 41800, 469.99512000000004, 173.9025879, 0, '5360', NULL, 50, 201, NULL, 'adsb_sample_500:187', 20573, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.712468+00:00', '704020', 'MMA506', 8.2475781, 100.3568029, 35250, 37650, 477.02628, 1.3183594, 706, '6166', false, 50, 201, NULL, 'adsb_sample_500:193', 21255, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.733585+00:00', '872fc2', 'ANA803', 3.6406589, 108.7730384, 39000, 41850, 513.94032, 232.9046631, -62, '6020', NULL, 50, 201, NULL, 'adsb_sample_500:195', 21483, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.743232+00:00', '461f55', 'FIN145', -3.1677318, 107.4913073, 39000, 41700, 484.71696000000003, 139.7680664, 0, '0747', NULL, 50, 201, NULL, 'adsb_sample_500:197', 21709, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.743347+00:00', 'c820d1', 'ANZ280', -1.9589996, 110.6084847, 40000, 42850, 505.15128, 302.7172852, 0, '0221', NULL, 50, 201, NULL, 'adsb_sample_500:199', 21935, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.743348+00:00', '885116', 'THA465', -0.9819031, 110.1389694, 39000, 41775, 491.52816, 138.1365967, 0, '6127', NULL, 50, 201, NULL, 'adsb_sample_500:200', 22048, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.743477+00:00', '86d624', 'TZP53', 3.6345434, 108.7648845, 39975, 42875, 509.1066, 232.9046631, -62, '3727', NULL, 50, 201, NULL, 'adsb_sample_500:201', 22161, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.743553+00:00', '750451', 'AXM5234', 1.8010712, 109.2884088, 24450, 26225, 408.91104, 101.9970703, -1475, '2326', NULL, 50, 201, NULL, 'adsb_sample_500:202', 22274, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.743553+00:00', '7821c6', 'CXA837', -1.0368991, 110.6102014, 36000, 38650, 452.19744000000003, 218.0841064, 0, '7006', NULL, 50, 201, NULL, 'adsb_sample_500:203', 22387, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.753463+00:00', '8a09bb', 'PAS212', -6.8451262, 111.7111301, 37000, 39650, 441.21096, 93.24646, -62, '2344', NULL, 50, 201, NULL, 'adsb_sample_500:205', 22593, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.837180+00:00', '895052', 'RBA874', 3.5520387, 106.1881614, 36975, 39650, 437.03604, 79.3322754, 125, '2157', NULL, 50, 201, NULL, 'adsb_sample_500:210', 23150, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.855587+00:00', '76b44e', 'SIA141', 2.0985389, 102.471242, 33000, 35375, 459.88775999999996, 151.875, 0, '5101', NULL, 50, 201, NULL, 'adsb_sample_500:218', 24046, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.866128+00:00', '780171', 'CPA725', 3.8327694, 103.5736942, 36000, 38575, 499.43843999999996, 263.6828613, -125, NULL, false, 50, 201, NULL, 'adsb_sample_500:222', 24499, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.916797+00:00', '7c146f', 'QFA52', -5.7776499, 112.3147559, 37000, 39675, 486.03528000000006, 126.0461426, 0, '0153', NULL, 50, 201, NULL, 'adsb_sample_500:225', 24836, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.926345+00:00', '8a09a0', 'BTK7521', -7.5066447, 112.4965453, 12350, 13275, 324.97560000000004, 100.9973145, -1281, '2410', false, 50, 201, NULL, 'adsb_sample_500:228', 25177, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.926398+00:00', '4bb10b', 'THY067', -4.4499779, 112.6734638, 34000, 36450, 515.9178, 330.2545166, 0, '4141', false, 50, 201, NULL, 'adsb_sample_500:229', 25290, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.926398+00:00', '8963f6', 'UAE398', -7.5576711, 113.3728981, 37850, 40575, 485.81532000000004, 125.6176758, -831, '6213', false, 50, 201, NULL, 'adsb_sample_500:230', 25404, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.926399+00:00', '76b459', 'SIA947', -6.9124174, 113.4754014, 36000, 38625, 466.69932, 315.5218506, -62, '4101', false, 50, 201, NULL, 'adsb_sample_500:231', 25518, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.926445+00:00', '06a104', 'QTR960', -6.9555688, 114.6426129, 38150, 40900, 501.85548000000006, 160.8068848, -1025, '2167', false, 50, 201, NULL, 'adsb_sample_500:233', 25746, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.926532+00:00', '8a1846', 'SMRG A', -7.0214009, 110.429163, NULL, 544, NULL, NULL, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:237', 26187, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.947111+00:00', '76b86d', 'TGW539', 1.1872315, 104.1036987, 5225, 5550, 239.72184000000001, 230.4107666, -1088, '5572', NULL, 50, 201, NULL, 'adsb_sample_500:239', 26396, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.957072+00:00', '7c8064', 'QFA255', 1.3453746, 103.9759183, 200, 225, 149.8536, 23.1481934, -894, '1370', NULL, 50, 201, NULL, 'adsb_sample_500:240', 26509, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.997779+00:00', '8a09c4', 'SJV201', -6.9862747, 112.1394897, 17825, 19075, 402.75864, 304.9914551, 1662, '6305', false, 50, 201, NULL, 'adsb_sample_500:252', 27814, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.997780+00:00', '8a0821', 'BTK7251', -7.3319793, 113.1339884, 7250, 7725, 247.85172, 152.6055908, -962, NULL, false, 50, 201, NULL, 'adsb_sample_500:253', 27928, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.997781+00:00', '484561', 'KLM836', -7.4215865, 113.9017439, 38000, 40725, 494.38476, 314.263916, 0, '4113', false, 50, 201, NULL, 'adsb_sample_500:254', 28037, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.997781+00:00', '8a057a', NULL, -7.3775339, 112.7943563, NULL, NULL, 8.56944, 8.4375, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:255', 28151, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.997781+00:00', '8a0a11', 'SJY273', -8.4544945, 115.0870872, 19150, 20450, 380.12687999999997, 281.8432617, 1919, '4401', false, 50, 201, NULL, 'adsb_sample_500:256', 28247, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.997782+00:00', '71c366', 'ABL569', -8.2032466, 115.1684546, 14725, 15750, 278.1738, 181.6479492, -1281, '4104', false, 50, 201, NULL, 'adsb_sample_500:257', 28361, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.997850+00:00', '7817fe', 'CXA891', -7.4813676, 115.1201534, 26375, 28350, 431.76276, 176.6821289, -1725, '0174', false, 50, 201, NULL, 'adsb_sample_500:260', 28693, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.997850+00:00', '8a0244', 'GIA424', -8.8779831, 114.3912148, 17525, 18700, 295.75187999999997, 141.0369873, -1344, NULL, false, 50, 201, NULL, 'adsb_sample_500:258', 28475, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.997850+00:00', '8a0509', 'CTV783', -5.9890723, 113.8238525, 35000, 37525, 450.43956000000003, 81.9580078, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:259', 28584, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.997879+00:00', '76cda1', 'SIA297', -9.5306826, 115.2127647, 39000, 41750, 499.87800000000004, 140.1965332, 0, '0130', false, 50, 201, NULL, 'adsb_sample_500:261', 28807, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.997905+00:00', '7822bc', 'CSN625', -4.9476886, 115.350759, 34000, 36625, 457.47072, 188.0419922, -62, '3112', false, 50, 201, NULL, 'adsb_sample_500:262', 28921, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.997905+00:00', '8a0827', 'BTK6231', -5.6562424, 113.0709028, 36025, 38600, 471.31343999999996, 263.1774902, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:263', 29035, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.997934+00:00', '76cdb1', 'SIA208', -8.9344382, 114.9216914, 40025, 42800, 477.24624, 315.4229736, -62, '1505', false, 50, 201, NULL, 'adsb_sample_500:265', 29253, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.997934+00:00', '8a1842', 'SRBY B', -7.374444, 112.8004932, NULL, 156, NULL, NULL, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:266', 29367, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:56.998798+00:00', '76b45a', 'SIA852', 6.0791731, 106.9344378, 31000, 33250, 444.72672, 48.2794189, 0, '2256', false, 50, 201, NULL, 'adsb_sample_500:267', 29467, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.007961+00:00', '76cd48', 'SIA38', 4.2107463, 107.5209618, 33950, 36375, 493.06644, 28.0700684, 894, '0136', false, 50, 201, NULL, 'adsb_sample_500:268', 29581, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.007962+00:00', '750319', 'MAS2628', 3.5648918, 106.8810081, 32475, 34825, 436.15728, 94.0759277, 450, NULL, false, 50, 201, NULL, 'adsb_sample_500:269', 29695, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.007962+00:00', '872fc2', 'ANA803', 3.6392212, 108.7711287, 39000, 41850, 513.94032, 232.9046631, -62, '6020', false, 50, 201, NULL, 'adsb_sample_500:270', 29804, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.007963+00:00', '86e058', 'TZP61', 4.2481256, 106.0894346, 39975, 42750, 503.83296, 251.9604492, 0, '3620', false, 50, 201, NULL, 'adsb_sample_500:271', 29918, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.008026+00:00', '8a095b', 'TNU860', 6.5722919, 106.022079, 35000, 37600, 462.3048, 351.293335, 0, '2404', false, 50, 201, NULL, 'adsb_sample_500:274', 30260, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.008057+00:00', '76b443', 'SIA175', 5.5950236, 104.8716474, 32750, 35125, 473.73048000000006, 187.2729492, -962, '5501', false, 50, 201, NULL, 'adsb_sample_500:277', 30572, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.008057+00:00', '8a18de', 'BAV6215', 3.363061, 106.2740564, NULL, NULL, NULL, NULL, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:276', 30477, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.008084+00:00', '7812dc', 'CCA871', 7.0028186, 105.4385805, 32000, 34300, 471.97260000000006, 211.8383789, -62, '0070', false, 50, 201, NULL, 'adsb_sample_500:278', 30686, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.008084+00:00', '8852e4', 'THA482', 3.8939238, 103.2510996, 39975, 42750, 499.87800000000004, 336.6650391, 0, '1463', false, 50, 201, NULL, 'adsb_sample_500:279', 30800, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.008111+00:00', '76cc81', 'SIA185', 5.1846242, 104.8894143, 40000, 42750, 486.91404000000006, 161.9384766, -62, '5571', false, 50, 201, NULL, 'adsb_sample_500:281', 31023, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.008198+00:00', '7818f5', 'CSN8048', 5.2025843, 105.6342101, 31000, 33250, 455.93244000000004, 33.0963135, 0, '2210', false, 50, 201, NULL, 'adsb_sample_500:282', 31137, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.008199+00:00', '75054b', 'AXM9035', 5.9584522, 104.9120092, 31950, 34225, 464.28228, 211.706543, 0, '5136', false, 50, 201, NULL, 'adsb_sample_500:284', 31364, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.008200+00:00', '76b451', 'SIA193', 5.3978276, 104.9440241, 36000, 38575, 470.87388000000004, 192.3815918, 0, '7053', false, 50, 201, NULL, 'adsb_sample_500:285', 31478, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.008251+00:00', '750238', 'FFM2575', 3.9500999, 108.3830667, 38000, 40650, 470.43467999999996, 260.458374, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:288', 31815, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.008251+00:00', 'a06310', 'FDX6826', 5.1075482, 105.2600956, 35025, 37500, 467.57808, 39.2706299, 0, '2234', false, 50, 201, NULL, 'adsb_sample_500:286', 31592, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.008287+00:00', '7822bb', 'CSN8353', 3.1771088, 106.4883757, 33000, 35450, 460.54692, 170.3759766, 0, '3156', false, 50, 201, NULL, 'adsb_sample_500:289', 31924, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.008344+00:00', '750571', 'MXD1004', 3.4807563, 106.4157629, 29000, 31050, 439.89264000000003, 79.9145508, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:290', 32038, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.008381+00:00', '8a1824', 'MATAK A', 3.3506584, 106.2597656, NULL, 156, NULL, NULL, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:291', 32147, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.008382+00:00', '71c524', 'JJA2641', 5.7794523, 107.2555518, 36000, 38575, 468.23724000000004, 221.7974854, 0, '4140', false, 50, 201, NULL, 'adsb_sample_500:293', 32361, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.008382+00:00', '76ceeb', 'SIA807', 6.9344759, 105.3228164, 36000, 38600, 508.66704, 232.0257568, 0, '0041', false, 50, 201, NULL, 'adsb_sample_500:292', 32247, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.018153+00:00', '8a0509', 'CTV783', -5.9892011, 113.8230157, 35000, 37525, 450.43956000000003, 81.9580078, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:295', 32589, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.018154+00:00', '8a064c', 'CTV527', -3.0288792, 106.289506, 31000, 33250, 432.20232, 170.2770996, 62, NULL, false, 50, 201, NULL, 'adsb_sample_500:296', 32698, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.018155+00:00', '885116', 'THA465', -0.9834695, 110.1403213, 39000, 41775, 491.52816, 138.1365967, 0, '6127', false, 50, 201, NULL, 'adsb_sample_500:297', 32807, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.018155+00:00', '89805e', 'ANG393', -1.6551375, 110.0686741, 33000, 35275, 462.3048, 123.1732178, 0, '5627', false, 50, 201, NULL, 'adsb_sample_500:298', 32921, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.018156+00:00', '7c5320', 'QFA24', 0.1597524, 108.7769008, 35000, 37550, 471.53303999999997, 144.9261475, -62, '0713', false, 50, 201, NULL, 'adsb_sample_500:299', 33035, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.018252+00:00', '8a1832', 'PKBUN B', -2.7048683, 111.6691375, NULL, 300, NULL, NULL, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:304', 33605, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.059274+00:00', '8a02ff', 'CTV171', -5.9642029, 109.2004752, 34000, 36425, 457.47072, 270.1263428, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:307', 33931, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.096437+00:00', '78212c', 'CSN365', 3.1435275, 101.8878293, 16100, 17150, 368.9208, 183.883667, -769, '3104', NULL, 50, 201, NULL, 'adsb_sample_500:309', 34149, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.099784+00:00', '8a099f', 'BTK7265', 3.4270906, 100.6108403, 22025, 23500, 392.43168000000003, 265.0286865, 0, '2124', NULL, 50, 201, NULL, 'adsb_sample_500:310', 34262, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.099786+00:00', '76b865', 'TGW740', 3.331883, 100.5495787, 34000, 36425, 485.81532000000004, 284.666748, 0, '2252', NULL, 50, 201, NULL, 'adsb_sample_500:311', 34375, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.110004+00:00', '8a08e9', 'SJV171', 0.3318214, 101.2043595, 34025, 36450, 470.43467999999996, 311.3800049, 62, '1736', NULL, 50, 201, NULL, 'adsb_sample_500:313', 34597, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.110005+00:00', '8963e6', 'UAE355', 3.3923507, 100.9630036, 38000, 40575, 503.61336, 290.088501, 0, '0166', NULL, 50, 201, NULL, 'adsb_sample_500:314', 34710, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.110006+00:00', '8a03f3', 'AWQ247', 2.2299027, 102.2642827, 35000, 37525, 433.30068, 139.4000244, 62, NULL, false, 50, 201, NULL, 'adsb_sample_500:316', 34932, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.110070+00:00', '76b44e', 'SIA141', 2.0996547, 102.4706626, 33000, 35375, 460.32732, 151.875, 0, '5101', NULL, 50, 201, NULL, 'adsb_sample_500:319', 35267, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.110070+00:00', '76b44f', 'SIA995', 2.3950624, 100.5640626, 28675, 30675, 435.49812000000003, 130.3417969, 831, '6730', NULL, 50, 201, NULL, 'adsb_sample_500:318', 35154, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.110099+00:00', '750324', 'AXM6047', 2.0537138, 102.6117468, 18200, 19500, 387.5976, 282.8155518, -1531, NULL, NULL, 50, 201, NULL, 'adsb_sample_500:320', 35380, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.110099+00:00', '76cce1', 'SIA9023', 4.3813562, 100.9265471, 41000, 43625, 461.42568, 141.8609619, 0, NULL, NULL, 50, 201, NULL, 'adsb_sample_500:321', 35491, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.110303+00:00', '750459', 'AXM5749', 2.7974367, 102.6665926, 20950, 22350, 393.75, 245.0610352, -3262, '0430', NULL, 50, 201, NULL, 'adsb_sample_500:328', 36285, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.110303+00:00', '8832a8', 'TLM105', 2.4663448, 103.8359928, 25725, 27450, 447.58296, 335.4400635, 1531, NULL, false, 50, 201, NULL, 'adsb_sample_500:329', 36398, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.110359+00:00', '885ca8', 'MJJ821', 3.7685466, 103.0989647, 38000, 40750, 482.95908000000003, 333.1713867, 0, '2265', false, 50, 201, NULL, 'adsb_sample_500:330', 36507, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.121147+00:00', '76d1cd', 'TGW247', 1.1462474, 104.2163515, 8175, 8650, 248.51088000000001, 265.3912354, -319, '6661', NULL, 50, 201, NULL, 'adsb_sample_500:332', 36732, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.130286+00:00', '7505a3', 'MAS487', 2.4136019, 99.8179793, 30200, 32275, 489.11148, 279.7723389, 706, '2140', NULL, 50, 201, NULL, 'adsb_sample_500:336', 37180, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.130956+00:00', '75059c', 'MAS724', 0.625577, 103.9812398, 38000, 40675, 453.73536, 348.1677246, 0, '2425', NULL, 50, 201, NULL, 'adsb_sample_500:337', 37293, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.142890+00:00', '76cc64', 'SIA621', 1.1435437, 103.9880204, 4850, 5150, 215.7714, 270.5328369, -962, '3622', NULL, 50, 201, NULL, 'adsb_sample_500:339', 37520, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.142987+00:00', '76cd17', 'SIA157', 2.8965926, 104.521265, 29350, 31425, 406.27439999999996, 226.4941406, -3325, '1635', NULL, 50, 201, NULL, 'adsb_sample_500:341', 37746, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.162269+00:00', '7503ab', NULL, 8.4372211, 100.5628395, 37000, 39525, 437.03604, 181.1810303, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:345', 38196, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.162270+00:00', '885315', 'THA268', 8.3126163, 100.3581548, 28000, 30000, 448.02252, 1.2799072, 1088, NULL, false, 50, 201, NULL, 'adsb_sample_500:346', 38299, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.223670+00:00', '8a03c7', NULL, -7.9007363, 110.0580955, 75, 125, 0.0, 180.0, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:351', 38863, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.234526+00:00', '885302', 'THA440', 4.2685103, 105.1840925, 33975, 36450, 486.47447999999997, 333.5394287, -62, NULL, false, 50, 201, NULL, 'adsb_sample_500:356', 39394, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.244019+00:00', '896112', 'UAE358', -2.1829319, 103.7402916, 35000, 37525, 479.00376, 127.2052002, 0, '1737', NULL, 50, 201, NULL, 'adsb_sample_500:357', 39503, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.244020+00:00', '8a02d4', 'GIA193', -0.9996271, 103.4511065, 37000, 39650, 445.82508, 140.8172607, 62, NULL, false, 50, 201, NULL, 'adsb_sample_500:358', 39616, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.244020+00:00', '8a0942', 'MYU6012', 0.8925962, 103.9249778, 40000, 42700, 432.20232, 347.8601074, 0, '2331', NULL, 50, 201, NULL, 'adsb_sample_500:359', 39725, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.244071+00:00', '8a0454', 'LNI316', -3.4949398, 114.5672536, 3575, 3925, 189.62387999999999, 16.237793, -125, '6331', false, 50, 201, NULL, 'adsb_sample_500:360', 39838, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.244071+00:00', '8a1812', 'LNI6001', -4.1743112, 114.5732617, 14850, 15900, 350.90315999999996, 350.4858398, -1219, '4405', false, 50, 201, NULL, 'adsb_sample_500:361', 39952, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.254120+00:00', '888158', 'VJC92', -1.1660099, 114.8622108, 35000, 37550, 455.05368000000004, 359.8736572, 62, '1501', false, 50, 201, NULL, 'adsb_sample_500:362', 40065, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.254121+00:00', '7823c8', 'CSN8137', -5.3778505, 114.1923237, 31950, 34375, 447.1434, 198.5174561, 194, '3133', false, 50, 201, NULL, 'adsb_sample_500:363', 40179, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.254122+00:00', '8a08de', 'SJV664', -4.3383765, 114.0588999, 23200, 24925, 310.03416000000004, 52.2070312, -1856, NULL, false, 50, 201, NULL, 'adsb_sample_500:364', 40293, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.254122+00:00', '8a1843', 'BJMASI B', -3.4418535, 114.7460175, NULL, 225, NULL, NULL, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:365', 40402, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.256521+00:00', '76cc67', 'SIA528', 3.7368107, 99.1587782, 37975, 40600, 518.11524, 281.3543701, -62, '0123', NULL, 50, 201, NULL, 'adsb_sample_500:366', 40502, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.264352+00:00', '70c0fc', 'OMA824', 3.8444209, 98.9643288, 31375, 33525, 479.88288, 290.3631592, 706, '2176', NULL, 50, 201, NULL, 'adsb_sample_500:367', 40615, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.264353+00:00', '8850af', 'THA436', 6.4690161, 102.2179985, 40050, 42775, 477.9054, 339.9334717, -62, NULL, false, 50, 201, NULL, 'adsb_sample_500:368', 40728, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.264672+00:00', '885105', 'THA410', 6.4950657, 102.2505927, 43000, 45600, 493.06644, 346.272583, 0, '0120', NULL, 50, 201, NULL, 'adsb_sample_500:369', 40837, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.274594+00:00', '8a099f', 'BTK7265', 3.4271765, 100.6116772, 22025, 23500, 392.43168000000003, 265.0286865, 0, '2124', NULL, 50, 201, NULL, 'adsb_sample_500:370', 40950, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.274595+00:00', '76cce1', 'SIA9023', 4.3796182, 100.9279418, 41000, 43625, 461.42568, 141.8609619, 0, '2234', NULL, 50, 201, NULL, 'adsb_sample_500:371', 41063, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.274596+00:00', '76b869', 'TGW784', 4.586513, 99.4293809, 34050, 36475, 478.56456000000003, 310.847168, 0, '0152', NULL, 50, 201, NULL, 'adsb_sample_500:373', 41289, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.274596+00:00', '801698', 'AXB629', 1.7125583, 100.537219, 37975, 40600, 472.85172000000006, 292.1154785, 0, '0170', NULL, 50, 201, NULL, 'adsb_sample_500:372', 41176, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.274597+00:00', '750458', 'AXM65', 4.7630668, 101.0125923, 31250, 33425, 466.25976, 336.6265869, 575, '2113', NULL, 50, 201, NULL, 'adsb_sample_500:374', 41402, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.274651+00:00', '8a07a7', 'MYU219', 3.6143088, 98.7951136, 5050, 5150, 247.63176, 308.4411621, 3394, '6720', NULL, 50, 201, NULL, 'adsb_sample_500:375', 41515, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.274692+00:00', '750441', 'AXM53', 4.4575524, 98.3576131, 34000, 36350, 476.58708, 298.4490967, 0, '2173', NULL, 50, 201, NULL, 'adsb_sample_500:376', 41628, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.274719+00:00', '750042', 'FFM1441', 4.1457725, 101.0338569, 13000, NULL, NULL, NULL, -62, NULL, false, 50, 201, NULL, 'adsb_sample_500:377', 41741, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.274753+00:00', '77044c', 'ALK309', 2.7281284, 96.3015389, 36000, 38400, 473.95007999999996, 290.1159668, 0, '0161', NULL, 50, 201, NULL, 'adsb_sample_500:378', 41850, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.274787+00:00', '76b448', 'SIA739', 4.7360301, 100.8465743, 37000, 39575, 439.23348, 141.5643311, 62, '0764', NULL, 50, 201, NULL, 'adsb_sample_500:379', 41963, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.274787+00:00', '8a09e4', 'PAS307', 3.1814647, 99.2690921, 16275, 17300, 370.45908000000003, 134.7802734, 1856, '4751', NULL, 50, 201, NULL, 'adsb_sample_500:380', 42076, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.274839+00:00', '750453', 'AXM13', 3.1305456, 101.1957121, 15875, 16825, 368.04204, 317.6422119, 2369, '2112', NULL, 50, 201, NULL, 'adsb_sample_500:381', 42189, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.274840+00:00', '8a1829', 'MEDAN', 3.6417103, 98.8853002, NULL, NULL, NULL, NULL, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:382', 42302, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.274875+00:00', '8963e6', 'UAE355', 3.3928657, 100.9616089, 38000, 40575, 503.61336, 290.088501, 0, '0166', NULL, 50, 201, NULL, 'adsb_sample_500:383', 42402, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.274876+00:00', '750287', 'AXM6327', 3.8587117, 100.7605076, 28900, 31025, 451.09872, 155.3686523, -894, NULL, false, 50, 201, NULL, 'adsb_sample_500:384', 42515, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.274911+00:00', '70e08d', 'KTC168', 3.6872649, 101.7722368, 20200, 21475, 380.56644, 29.597168, 1406, NULL, false, 50, 201, NULL, 'adsb_sample_500:386', 42737, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.274911+00:00', 'a0105b', 'FDX6020', 3.7717652, 101.4317465, 17150, 18200, 430.00488, 349.6838379, 1919, '2167', NULL, 50, 201, NULL, 'adsb_sample_500:385', 42624, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.274912+00:00', '75010b', 'AXM103', 4.4017196, 101.1707139, 28175, 30150, 442.30967999999996, 335.9838867, 831, NULL, false, 50, 201, NULL, 'adsb_sample_500:387', 42846, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.295288+00:00', '8a09ca', 'PAS113', -5.9633875, 108.9074707, 36000, 38625, 446.48424, 270.1263428, 0, '4420', NULL, 50, 201, NULL, 'adsb_sample_500:388', 42955, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.305333+00:00', '8a0aa0', 'MYU9903', 0.49299, 104.6365786, 25200, 26850, 405.39564, 163.394165, 2112, '2206', NULL, 50, 201, NULL, 'adsb_sample_500:390', 43177, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.315030+00:00', '8a08fb', NULL, 1.3800073, 97.4070168, NULL, NULL, NULL, NULL, NULL, NULL, false, 50, 201, NULL, 'adsb_sample_500:391', 43290, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.315467+00:00', '76cccd', 'SIA7822', 1.3866162, 104.0080833, 2375, 2450, 181.2744, 23.0328369, 894, '0121', NULL, 50, 201, NULL, 'adsb_sample_500:392', 43383, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.325688+00:00', '758384', 'PAL502', 2.2788262, 106.4829469, 30900, 33100, 467.13852, 37.7050781, 769, '2262', NULL, 50, 201, NULL, 'adsb_sample_500:393', 43496, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.325689+00:00', '76b44e', 'SIA141', 2.0973802, 102.4718642, 33000, 35375, 459.88775999999996, 151.875, 0, '5101', NULL, 50, 201, NULL, 'adsb_sample_500:394', 43610, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.335587+00:00', '7504ec', 'AXM5195', 3.6146522, 106.1098838, 34000, 36550, 481.42080000000004, 270.1208496, -62, '0466', NULL, 50, 201, NULL, 'adsb_sample_500:397', 43951, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.335588+00:00', '76cd76', 'SIA221', 1.3732052, 104.3109155, 8825, 9275, 365.18544, 114.7412109, 1475, '2215', NULL, 50, 201, NULL, 'adsb_sample_500:398', 44064, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.376972+00:00', 'ac498c', 'FDX6124', 1.9599867, 103.8989496, 16250, 17275, 417.26088, 356.2976074, 2625, '2000', NULL, 50, 201, NULL, 'adsb_sample_500:399', 44177, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.387515+00:00', '76b441', 'SIA948', -0.0468421, 105.5381656, 30325, 32525, 441.21096, 119.8718262, 894, '2245', NULL, 50, 201, NULL, 'adsb_sample_500:400', 44290, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.396876+00:00', '8a07b7', 'AWQ327', 1.0082316, 103.5328388, 31000, 33275, 462.08484, 133.0718994, 125, NULL, false, 50, 201, NULL, 'adsb_sample_500:401', 44403, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.396877+00:00', '750281', 'MAS2585', 2.8769159, 102.4866056, 18250, 19425, 379.46772, 235.7226562, -2562, NULL, false, 50, 201, NULL, 'adsb_sample_500:403', 44625, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.396877+00:00', '76cd0f', 'SIA633', 2.5344515, 107.3176289, 40000, 42750, 511.08408000000003, 232.8607178, 0, '3220', NULL, 50, 201, NULL, 'adsb_sample_500:402', 44512, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.396929+00:00', '75020f', NULL, 3.0316257, 104.6341324, 38000, 40700, 468.4572, 276.4874268, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:404', 44734, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.397373+00:00', '76cc6d', 'SIA929', 1.17028, 104.7410989, 14950, 16000, 384.74136, 267.9180908, -1856, '7007', NULL, 50, 201, NULL, 'adsb_sample_500:405', 44837, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.406926+00:00', '8003b3', 'AXB660', 3.9430833, 95.9720135, 35000, 37275, 453.95496, 107.0397949, 0, '0662', false, 50, 201, NULL, 'adsb_sample_500:406', 44950, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.407393+00:00', '8a03ab', 'CTV667', -5.9619498, 107.4824667, 12025, 12875, 306.95796, 270.1867676, -1344, NULL, false, 50, 201, NULL, 'adsb_sample_500:407', 45064, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.417391+00:00', '78143a', 'CXA8683', -5.7958889, 106.9049335, 5925, 6300, 261.91404, 167.8765869, -831, '6240', false, 50, 201, NULL, 'adsb_sample_500:408', 45173, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.417436+00:00', '8a074b', 'CTV955', -3.810904, 105.5597305, 32975, 35400, 462.96396, 141.0479736, -62, NULL, false, 50, 201, NULL, 'adsb_sample_500:409', 45287, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.417437+00:00', '7c4928', 'QFA82', -3.5714793, 109.8909402, 39000, 41725, 485.37611999999996, 128.4741211, 0, '2243', false, 50, 201, NULL, 'adsb_sample_500:410', 45396, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.417480+00:00', '8a1939', 'FLTH03', -6.1241269, 106.642828, NULL, NULL, 0.87876, 0.0, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:411', 45510, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.417540+00:00', '8a0a67', 'TNU698', -3.3050179, 106.016264, 32975, 35375, 443.18844, 158.7030029, 0, '2546', false, 50, 201, NULL, 'adsb_sample_500:412', 45613, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.417575+00:00', '750597', 'MAS251', -3.2769513, 106.5836263, 37000, 39650, 477.46584, 150.1062012, 0, '2376', false, 50, 201, NULL, 'adsb_sample_500:413', 45727, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.417606+00:00', '76cda5', 'SIA967', -3.6909127, 105.1916671, 39525, 42250, 488.23235999999997, 342.6031494, 1150, '2414', false, 50, 201, NULL, 'adsb_sample_500:415', 45947, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.417606+00:00', '8a09c2', 'TNU5106', -6.1108661, 106.6691566, NULL, NULL, 10.10736, 67.5, NULL, '2421', true, 50, 201, NULL, 'adsb_sample_500:414', 45841, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.417640+00:00', '500567', 'T7JRG', -6.2362003, 106.9573545, 1325, 1400, 146.7774, 245.0061035, -831, '5035', false, 50, 201, NULL, 'adsb_sample_500:416', 46061, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.417641+00:00', '8a093b', 'BTK6887', -6.0885715, 106.7077804, 900, 950, 139.52628, 247.6647949, -706, '4763', false, 50, 201, NULL, 'adsb_sample_500:417', 46175, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.417679+00:00', '8a04e4', 'BTK7162', -4.2275476, 106.3621402, 34000, 36450, 462.74399999999997, 157.6483154, -894, '5471', false, 50, 201, NULL, 'adsb_sample_500:418', 46289, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.417687+00:00', '8a06d0', 'CTV986', -4.3370461, 105.4517126, 26000, 27850, 413.74512, 332.8143311, 62, NULL, false, 50, 201, NULL, 'adsb_sample_500:419', 46403, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.417719+00:00', '750517', 'AXM354', -5.6425309, 106.2541866, 17350, 18500, 380.34684000000004, 327.5628662, 1219, '2312', false, 50, 201, NULL, 'adsb_sample_500:420', 46512, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.417720+00:00', '8a04a4', 'CTV216', -6.3780785, 107.1798277, 16900, 18000, 386.05967999999996, 103.1726074, 1662, NULL, false, 50, 201, NULL, 'adsb_sample_500:421', 46626, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.417753+00:00', '8a0604', 'BTK6269', -6.0305715, 106.9245458, 4950, 5300, 206.1036, 248.6645508, -769, '5020', false, 50, 201, NULL, 'adsb_sample_500:423', 46849, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.417790+00:00', '780acf', 'CCA475', -6.0253572, 106.8381357, 3225, 3450, 187.6464, 222.62146, -831, '1527', false, 50, 201, NULL, 'adsb_sample_500:424', 46963, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.417791+00:00', '8a1829', 'SOETA B', -6.1255002, 106.6590714, NULL, 294, NULL, NULL, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:425', 47077, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.417842+00:00', '8a0376', NULL, -6.1214232, 106.6451025, NULL, NULL, 10.54692, 247.5, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:426', 47177, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.417842+00:00', '8a0838', 'LNI383', -6.1197066, 106.7008281, 625, 675, 154.90728, 248.4063721, -769, '4714', false, 50, 201, NULL, 'adsb_sample_500:427', 47273, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.417843+00:00', '8a1915', 'AMC T1F', -6.1313581, 106.6507459, NULL, NULL, 13.40316, 78.75, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:428', 47387, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.417871+00:00', 'b2b177', NULL, 2.4100184, 96.3300133, NULL, NULL, NULL, NULL, NULL, NULL, false, 50, 201, NULL, 'adsb_sample_500:429', 47490, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.437279+00:00', '8a09b8', 'AWQ211', 0.4501176, 104.1124535, 35000, 37575, 464.06232, 134.7363281, 62, '2161', NULL, 50, 201, NULL, 'adsb_sample_500:430', 47583, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.458206+00:00', '76cd02', 'SIA235', 0.7631421, 104.5581508, 14175, 15075, 377.49024000000003, 164.3444824, 894, '0126', NULL, 50, 201, NULL, 'adsb_sample_500:431', 47696, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.468056+00:00', '8a074d', 'CTV882', -1.1346602, 102.5197792, 34000, 36475, 453.51576, 316.7852783, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:432', 47809, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.468659+00:00', 'b1b173', NULL, 0.9200191, 104.5200205, NULL, NULL, NULL, NULL, NULL, NULL, false, 50, 201, NULL, 'adsb_sample_500:433', 47918, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.478239+00:00', '896121', 'UAE369', 2.2961426, 102.8924131, 32000, 34275, 511.08408000000003, 286.3476562, 0, '4127', NULL, 50, 201, NULL, 'adsb_sample_500:434', 48011, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.478240+00:00', '7c492a', 'QFA1', 0.9527421, 105.3924036, 24675, 26450, 393.5304, 307.8863525, -575, '1334', NULL, 50, 201, NULL, 'adsb_sample_500:435', 48124, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.478241+00:00', '76d256', 'TGW279', -2.8887177, 104.7312069, 35975, 38600, 458.34947999999997, 347.4151611, -62, NULL, false, 50, 201, NULL, 'adsb_sample_500:436', 48237, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.478709+00:00', '8a0ab8', 'TNU679', 2.2625828, 102.6866984, 22425, 23925, 381.66516, 316.9116211, -381, '2436', NULL, 50, 201, NULL, 'adsb_sample_500:437', 48346, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.488307+00:00', '8832a8', 'TLM105', 2.4670744, 103.8356709, 25750, 27500, 446.9238, 335.4400635, 1538, NULL, false, 50, 201, NULL, 'adsb_sample_500:438', 48459, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.488308+00:00', '76cc75', 'SIA601', 1.2855506, 103.9506412, 1375, 1450, 156.2256, 22.9559326, -894, '7105', NULL, 50, 201, NULL, 'adsb_sample_500:439', 48568, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.488309+00:00', '76b453', 'SIA921', 2.0289946, 106.6567111, 36000, 38600, 468.8964, 232.6190186, 0, '6512', NULL, 50, 201, NULL, 'adsb_sample_500:440', 48681, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.519518+00:00', '8a09c4', 'SJV201', -6.9858027, 112.138803, 17825, 19075, 402.31944000000004, 304.9914551, 1662, '6305', NULL, 50, 201, NULL, 'adsb_sample_500:441', 48794, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.529249+00:00', '7c146a', 'QFA36', -10.7913208, 110.8873701, 37000, 39600, 487.5732, 156.3244629, 62, '0102', NULL, 50, 201, NULL, 'adsb_sample_500:442', 48907, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.529708+00:00', '76cd15', 'SIA522', 4.6953464, 94.3196654, 34000, 36200, 520.75188, 281.0742188, 0, '2263', false, 50, 201, NULL, 'adsb_sample_500:443', 49020, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.539399+00:00', '76b44a', 'SIA534', 4.6156311, 94.5570517, 36000, 38375, 479.22372, 281.8048096, 0, '2212', false, 50, 201, NULL, 'adsb_sample_500:444', 49134, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.567528+00:00', '75027d', 'AXM379', -0.6161141, 106.582489, 38000, 40650, 457.91028000000006, 308.973999, -62, NULL, false, 50, 201, NULL, 'adsb_sample_500:445', 49248, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.570913+00:00', '7820fb', 'CHH702', -0.6545663, 104.2332172, 30000, 32200, 452.8566, 349.3103027, 0, '2426', NULL, 50, 201, NULL, 'adsb_sample_500:446', 49357, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.580385+00:00', '8a0a1e', 'BTK6884', -2.7566886, 103.634119, 34000, 36475, 467.35847999999993, 317.9498291, 0, '2540', NULL, 50, 201, NULL, 'adsb_sample_500:447', 49470, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.580387+00:00', '8a03aa', 'CTV887', -2.783339, 104.8960233, 37025, 39650, 446.9238, 140.7183838, 62, NULL, false, 50, 201, NULL, 'adsb_sample_500:449', 49696, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.580387+00:00', '8a082a', 'LNI257', -2.47967, 103.707912, 33025, 35400, 457.03116000000006, 116.2298584, 0, '6254', NULL, 50, 201, NULL, 'adsb_sample_500:450', 49805, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.580388+00:00', '7502d9', 'MXD172', -0.4188538, 105.8996415, 36000, 38625, 452.8566, 323.7121582, 62, '4123', NULL, 50, 201, NULL, 'adsb_sample_500:452', 50018, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.580388+00:00', '8a074b', 'CTV955', -3.8102603, 105.5591941, 32975, 35375, 462.96396, 141.0479736, -62, NULL, false, 50, 201, NULL, 'adsb_sample_500:453', 50131, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.580388+00:00', 'ddeeff', 'PALEMB', -2.9002833, 104.7000074, NULL, NULL, NULL, NULL, NULL, NULL, true, 50, 201, NULL, 'adsb_sample_500:451', 49918, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.580545+00:00', '76cd03', 'SIA204', 0.0805306, 107.4373412, 43000, 45700, 485.59572, 303.4918213, 0, '1145', NULL, 50, 201, NULL, 'adsb_sample_500:455', 50353, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.591049+00:00', '770588', 'ALK605', -4.4308805, 101.1203957, 40000, 42725, 474.82919999999996, 312.522583, 0, '1257', NULL, 50, 201, NULL, 'adsb_sample_500:456', 50466, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.591050+00:00', '780cb9', 'CCA977', 0.8111215, 106.8607521, 37000, 39700, 471.31343999999996, 169.8596191, 0, '0072', NULL, 50, 201, NULL, 'adsb_sample_500:457', 50579, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.591051+00:00', '7c6bbd', 'JST8', -4.0566587, 107.502358, 38975, 41750, 488.01275999999996, 153.0670166, 62, '0151', NULL, 50, 201, NULL, 'adsb_sample_500:458', 50692, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.591120+00:00', '8a03c8', 'GIA839', -2.1796274, 106.1415768, 35000, 37450, 437.47560000000004, 160.3619385, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:459', 50805, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.591121+00:00', '750594', 'MAS147', -3.1381416, 106.1554384, 35000, 37550, 479.66292, 155.6268311, 0, '2152', NULL, 50, 201, NULL, 'adsb_sample_500:463', 51245, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.591121+00:00', '7822bb', 'CSN8353', 3.1761003, 106.4885688, 33000, 35450, 459.88775999999996, 170.3759766, 0, '3156', NULL, 50, 201, NULL, 'adsb_sample_500:462', 51132, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.591121+00:00', '8a02d4', 'GIA193', -0.9989619, 103.4506345, 37000, 39650, 446.26464, 140.8172607, 62, NULL, false, 50, 201, NULL, 'adsb_sample_500:461', 51023, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.591121+00:00', '8a064c', 'CTV527', -3.0300808, 106.2896991, 31000, 33250, 432.20232, 170.2770996, 125, NULL, false, 50, 201, NULL, 'adsb_sample_500:460', 50914, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.591122+00:00', '750597', 'MAS251', -3.2780242, 106.5842485, 37000, 39650, 477.46584, 150.1062012, 0, '2376', NULL, 50, 201, NULL, 'adsb_sample_500:464', 51358, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.593689+00:00', '76cc6a', 'SIA945', 0.841248, 105.1686645, 22925, 24500, 438.35436, 312.0446777, -1981, '4122', NULL, 50, 201, NULL, 'adsb_sample_500:465', 51471, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.593690+00:00', '7502ad', 'AXM1730', 1.4980888, 104.0489602, 6875, 7225, 266.74812000000003, 352.902832, 3712, NULL, false, 50, 201, NULL, 'adsb_sample_500:466', 51584, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.602200+00:00', '75021f', 'MAS2532', 2.7777815, 105.6027102, 35000, 37525, 433.74024000000003, 103.7164307, -62, NULL, false, 50, 201, NULL, 'adsb_sample_500:467', 51693, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.611198+00:00', '750324', 'AXM6047', 2.0539284, 102.6108027, 18175, 19450, 386.27928, 282.8485107, -1538, '0335', NULL, 50, 201, NULL, 'adsb_sample_500:468', 51802, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.611199+00:00', '75031a', 'MAS610', 2.3095965, 102.9381609, 24000, 25625, 384.0822, 243.4350586, 0, NULL, false, 50, 201, NULL, 'adsb_sample_500:469', 51915, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.611199+00:00', '76cd07', 'SIA510', 4.8553562, 93.4040666, 40000, 42475, 508.88664, 281.9036865, 0, '2222', false, 50, 201, NULL, 'adsb_sample_500:470', 52024, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.611200+00:00', '06a117', 'QTR963', 3.33184, 95.8681154, 38000, 40475, 511.08408000000003, 266.2976074, 0, '4115', false, 50, 201, NULL, 'adsb_sample_500:472', 52252, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.611200+00:00', '76cd0d', 'SIA516', 7.5586796, 98.9026594, 40000, 42575, 515.6982, 313.192749, 0, '2261', false, 50, 201, NULL, 'adsb_sample_500:471', 52138, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.611201+00:00', '896327', 'ETD477', 5.4444337, 94.7454286, 32000, 34125, 513.50112, 288.5064697, 0, '4114', false, 50, 201, NULL, 'adsb_sample_500:473', 52366, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.644506+00:00', '76cd11', 'SIA438', 3.2494426, 96.0776711, 40000, 42525, 508.00788, 267.2973633, 0, '0103', NULL, 50, 201, NULL, 'adsb_sample_500:474', 52480, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.652177+00:00', '8851e7', 'THA401', 1.2031531, 103.9163089, 2550, 2675, 190.94256, 21.4672852, 256, '0746', NULL, 50, 201, NULL, 'adsb_sample_500:475', 52593, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.668547+00:00', '8a044e', 'GIA324', -6.5120173, 109.4720435, 33000, 35325, 441.65052000000003, 104.0020752, 62, NULL, false, 50, 201, NULL, 'adsb_sample_500:476', 52707, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.672976+00:00', '8a061e', 'CTV684', -7.6517415, 113.0009937, 34950, 37500, 445.60548, 112.5384521, -62, NULL, false, 50, 201, NULL, 'adsb_sample_500:477', 52816, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.672977+00:00', '8a0574', 'LNI664', -7.2850299, 110.9695959, 24900, 26650, 418.13964, 44.0332031, 638, '4650', NULL, 50, 201, NULL, 'adsb_sample_500:478', 52925, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.682889+00:00', '8a09f8', 'TNU5110', -6.7064667, 110.0333762, 39000, 41775, 451.97748, 101.7333984, 62, '2334', NULL, 50, 201, NULL, 'adsb_sample_500:479', 53038, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.701149+00:00', '06a138', 'QTR847', 8.0008364, 95.3387117, 34000, 36250, 508.22748, 268.7585449, 0, '0752', false, 50, 201, NULL, 'adsb_sample_500:480', 53151, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.702729+00:00', '704020', 'MMA506', 8.249681, 100.3568029, 35250, 37650, 477.02628, 1.3183594, 769, '6166', false, 50, 201, NULL, 'adsb_sample_500:481', 53265, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.702730+00:00', '76d1c7', 'TGW732', 3.5024929, 95.9114599, 34025, 36325, 482.95908000000003, 266.3195801, 0, '2201', false, 50, 201, NULL, 'adsb_sample_500:483', 53493, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.702730+00:00', 'ac954d', 'N91LA', 6.5834284, 99.1291237, 38000, 40650, 522.29016, 290.2752686, 0, '2223', false, 50, 201, NULL, 'adsb_sample_500:482', 53379, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.702731+00:00', '896713', 'ETD425', 8.0743504, 97.5155497, 28225, 30100, 466.04016, 269.1375732, 769, '6160', false, 50, 201, NULL, 'adsb_sample_500:484', 53607, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.723843+00:00', '780cb9', 'CCA977', 0.8092546, 106.8611169, 37000, 39700, 471.31343999999996, 169.8596191, 0, '0072', NULL, 50, 201, NULL, 'adsb_sample_500:485', 53721, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.733825+00:00', '782472', 'CQH7199', -2.4187517, 107.739315, 33000, 35400, 433.95984, 165.9979248, 62, '3124', NULL, 50, 201, NULL, 'adsb_sample_500:486', 53834, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.743535+00:00', '7801b4', 'CPA797', 2.2492576, 106.8140602, 39000, 41800, 470.65428, 173.9025879, 0, '5360', NULL, 50, 201, NULL, 'adsb_sample_500:487', 53947, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.743536+00:00', '461f55', 'FIN145', -3.1696415, 107.4928951, 39000, 41700, 484.71696000000003, 139.7680664, 0, '0747', NULL, 50, 201, NULL, 'adsb_sample_500:488', 54060, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.743537+00:00', '76cc6b', 'SIA276', -1.7700434, 107.9292154, 37975, 40700, 500.53716, 320.2679443, -62, '1546', NULL, 50, 201, NULL, 'adsb_sample_500:490', 54286, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.743537+00:00', '89805e', 'ANG393', -1.6557384, 110.0695539, 33000, 35275, 463.18356, 123.1072998, 0, '5627', NULL, 50, 201, NULL, 'adsb_sample_500:489', 54173, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.743538+00:00', '750451', 'AXM5234', 1.800642, 109.2903399, 24425, 26200, 408.03228, 102.0245361, -1538, '2326', NULL, 50, 201, NULL, 'adsb_sample_500:492', 54512, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.743538+00:00', 'c820d1', 'ANZ280', -1.9577122, 110.6065321, 40000, 42850, 505.15128, 302.7172852, -62, '0221', NULL, 50, 201, NULL, 'adsb_sample_500:491', 54399, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.743539+00:00', '750599', 'MAS145', -0.7608461, 106.2357974, 37000, 39625, 463.18356, 144.0472412, 62, '2165', NULL, 50, 201, NULL, 'adsb_sample_500:493', 54625, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.743601+00:00', '86d624', 'TZP53', 3.633256, 108.7631893, 39975, 42875, 509.1066, 232.9046631, -62, '3727', NULL, 50, 201, NULL, 'adsb_sample_500:494', 54738, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.743602+00:00', '7821c6', 'CXA837', -1.0385299, 110.6089354, 36000, 38650, 452.19744000000003, 218.0841064, 0, '7006', NULL, 50, 201, NULL, 'adsb_sample_500:495', 54851, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.764140+00:00', '8a08f8', NULL, -7.9000068, 110.0660133, NULL, NULL, NULL, NULL, NULL, NULL, false, 50, 201, NULL, 'adsb_sample_500:496', 54964, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.774794+00:00', '8a02d5', 'GIA415', -5.9632802, 108.4982729, 30050, 32225, 424.51164, 270.1373291, -2112, NULL, false, 50, 201, NULL, 'adsb_sample_500:497', 55057, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.806450+00:00', '75054c', 'MAS160', 4.4725084, 95.5383539, 32000, 34075, 523.60848, 281.0083008, 0, '2135', false, 50, 201, NULL, 'adsb_sample_500:498', 55166, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.814876+00:00', '8017f2', 'IGO1512', 5.7440257, 96.1820841, 36000, 38400, 483.61824, 290.8355713, 0, '4116', false, 50, 201, NULL, 'adsb_sample_500:499', 55280, '{}'::text[])
ON CONFLICT DO NOTHING;
INSERT INTO telemetry (ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags)
VALUES ('2024-12-30T04:49:57.814877+00:00', '76b86b', 'TGW653', 6.5403628, 99.5912576, 32550, 34875, 459.6678, 138.0871582, 1088, '6150', false, 50, 201, NULL, 'adsb_sample_500:500', 55394, '{}'::text[])
ON CONFLICT DO NOTHING;

INSERT INTO quarantine (recording_id, raw_ref, step_code, reason)
VALUES ('adsb_sample_500', 'adsb_sample_500:129', 'position_jumps', 'Implied speed to its neighbours above 1,200 kt.')
ON CONFLICT DO NOTHING;

COMMIT;
