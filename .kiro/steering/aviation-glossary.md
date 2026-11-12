---
inclusion: fileMatch
fileMatchPattern: ["services/pipeline/**", "fixtures/**"]
---
# Aviation glossary

- **ASTERIX:** EUROCONTROL's binary format for surveillance data. Each data block has a
  category, a length and one or more records.
- **CAT021:** the ASTERIX category for ADS-B target reports (aircraft broadcasting their own
  position). Fields are "data items" named I021/xxx; check the CAT021 edition of the
  recordings we use before relying on any item number.
- **SAC / SIC:** System Area Code and System Identification Code; together they identify
  the ground station that produced the record.
- **ICAO24:** the aircraft's 24-bit address, written as 6 hex characters.
- **Track number:** the ground system's id for a track; not unique across stations.
- **Squawk (Mode 3/A code):** 4 octal digits; 7500 = hijack, 7600 = radio failure,
  7700 = general emergency.
- **Go-around:** an approach abandoned near the runway, followed by a climb.
- **Holding:** a racetrack pattern flown while waiting, usually repeated.
- **raw_ref:** our pointer to one record: `<recording_file_id>:<record_index>`.
- **Replay:** playing a recording through the pipeline on the shared clock (C6).
