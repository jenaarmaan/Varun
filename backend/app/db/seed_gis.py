import sys
import os
from sqlalchemy import func
from sqlalchemy.orm import Session

# Add backend root to sys.path to enable app imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, sync_engine
from app.db.models import GraphNode, GraphEdge


def seed_weather_graph():
    """Seeds district, river, reservoir, and school nodes for the pilot."""
    print("Initializing Weather Intelligence Graph Seeder...")
    session = SessionLocal()
    try:
        # Check if PostGIS extension exists, if not, create it
        try:
            session.execute(func.now())
            session.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
            session.commit()
            print("PostGIS extension checked/created successfully.")
        except Exception as e:
            session.rollback()
            print(f"Warning: Failed to enable PostGIS extension: {e}. PostGIS may already be enabled or database permissions are restricted.")

        # Clean existing nodes and edges to prevent duplicate keys during seeds
        print("Clearing existing Graph relationships...")
        session.query(GraphEdge).delete()
        session.query(GraphNode).delete()
        session.commit()

        # 1. Add Graph Nodes (Districts, Rivers, Reservoirs, Schools, Hospitals, Weather Events)
        print("Inserting Graph Nodes...")
        nodes = [
            # Districts (LGD codes)
            GraphNode(
                id="district_21",  # LGD code for Bhubaneswar / Khordha, Odisha
                name="Khordha (Bhubaneswar)",
                type="district",
                properties={"state": "Odisha", "population": 2251000},
                geom=func.ST_GeomFromText("POLYGON((85.5 20.1, 85.9 20.1, 85.9 20.5, 85.5 20.5, 85.5 20.1))", 4326)
            ),
            GraphNode(
                id="district_29",  # LGD code for Mysuru, Karnataka
                name="Mysuru",
                type="district",
                properties={"state": "Karnataka", "population": 3001000},
                geom=func.ST_GeomFromText("POLYGON((76.3 12.1, 76.8 12.1, 76.8 12.6, 76.3 12.6, 76.3 12.1))", 4326)
            ),
            # Rivers
            GraphNode(
                id="river_cauvery",
                name="Cauvery River",
                type="river",
                properties={"length_km": 800},
                geom=func.ST_GeomFromText("LINESTRING(75.7 12.4, 76.5 12.4, 77.0 12.3, 78.0 11.5)", 4326)
            ),
            GraphNode(
                id="river_mahanadi",
                name="Mahanadi River",
                type="river",
                properties={"length_km": 858},
                geom=func.ST_GeomFromText("LINESTRING(81.8 20.3, 83.5 20.8, 85.2 20.5, 85.8 20.2)", 4326)
            ),
            # Reservoirs
            GraphNode(
                id="reservoir_kr_sagar",
                name="Krishna Raja Sagara",
                type="reservoir",
                properties={"max_capacity_tmc": 49.45, "current_level_ft": 124.8},
                geom=func.ST_GeomFromText("POINT(76.57 12.44)", 4326)
            ),
            # Critical Infrastructure
            GraphNode(
                id="school_mysuru_public",
                name="Mysuru Public School",
                type="school",
                properties={"student_count": 1200, "shelter_capacity": 400},
                geom=func.ST_GeomFromText("POINT(76.64 12.31)", 4326)
            ),
            GraphNode(
                id="hospital_bhubaneswar_general",
                name="Bhubaneswar General Hospital",
                type="hospital",
                properties={"bed_count": 500, "icu_beds": 50},
                geom=func.ST_GeomFromText("POINT(85.82 20.29)", 4326)
            ),
            GraphNode(
                id="power_station_mysuru_grid",
                name="Mysuru Power Grid Substation",
                type="power_station",
                properties={"voltage_kv": 220, "criticality": "HIGH"},
                geom=func.ST_GeomFromText("POINT(76.62 12.33)", 4326)
            )
        ]
        session.add_all(nodes)
        session.commit()
        print("Graph Nodes seeded successfully.")

        # 2. Add Graph Edges
        print("Inserting Graph Edges (Relationships)...")
        edges = [
            # Located_in relationships
            GraphEdge(source_id="reservoir_kr_sagar", target_id="district_29", type="located_in", properties={}),
            GraphEdge(source_id="school_mysuru_public", target_id="district_29", type="located_in", properties={}),
            GraphEdge(source_id="power_station_mysuru_grid", target_id="district_29", type="located_in", properties={}),
            GraphEdge(source_id="hospital_bhubaneswar_general", target_id="district_21", type="located_in", properties={}),
            
            # Flow & downstream relationships
            GraphEdge(source_id="reservoir_kr_sagar", target_id="river_cauvery", type="connected_to", properties={}),
            GraphEdge(source_id="reservoir_kr_sagar", target_id="school_mysuru_public", type="downstream_of", properties={"distance_km": 15}),
            GraphEdge(source_id="reservoir_kr_sagar", target_id="power_station_mysuru_grid", type="downstream_of", properties={"distance_km": 12})
        ]
        session.add_all(edges)
        session.commit()
        print("Graph Edges seeded successfully.")

    except Exception as e:
        session.rollback()
        print(f"Error occurred during graph seeding: {e}")
        raise e
    finally:
        session.close()


if __name__ == "__main__":
    seed_weather_graph()
