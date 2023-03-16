SELECT
    load_extension('mod_spatialite')
;

SELECT
    InitSpatialMetaData('None')
;

-- We haven't converted to using a CRS yet
-- INSERT INTO
--     spatial_ref_sys (
--         srid, auth_name, auth_srid,
--         ref_sys_name, proj4text, srtext
--     )
-- VALUES
--     (
--         37008,
--         'esri',
--         37008,
--         'Authalic sphere (ARC/INFO)',
--         '+proj=longlat +ellps=sphere +no_defs +type=crs',
--         'GEOGCRS[ ""GCS_Sphere_ARC_INFO "", DATUM[ ""D_Sphere_ARC_INFO "", ELLIPSOID[ ""Sphere_ARC_INFO "",6370997,0, LENGTHUNIT[ ""metre "",1]]], PRIMEM[ ""Greenwich "",0, ANGLEUNIT[ ""degree "",0.0174532925199433]], CS[ellipsoidal,2], AXIS[ ""geodetic latitude (Lat) "",north, ORDER[1], ANGLEUNIT[ ""degree "",0.0174532925199433]], AXIS[ ""geodetic longitude (Lon) "",east, ORDER[2], ANGLEUNIT[ ""degree "",0.0174532925199433]], USAGE[ SCOPE[ ""Not known. ""], AREA[ ""World. ""], BBOX[-90,-180,90,180]], ID[ ""ESRI "",37008]]'
--     )
-- ;

-- Create a placeholder for the CRS
INSERT INTO
    spatial_ref_sys (
        srid, auth_name, auth_srid,
        ref_sys_name, proj4text, srtext
    )
VALUES
    (
        347895,
        'EPSG',
        347895,
        'WGS 84 / UTM zone 19N',
        '+proj=utm +zone=19 +datum=WGS84 +units=m +no_defs',
        'PROJCS["WGS 84 / UTM zone 19N",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",-69],PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH],AUTHORITY["EPSG","32619"]]'
    )
;

CREATE TABLE Shoreline (
    id INT PRIMARY KEY
);

SELECT
    AddGeometryColumn(
        'Shoreline',
        'loc',
        347895,
        'POINT',
        'XY',
        1
    )
;

CREATE TABLE RiverNodes (
    id INT PRIMARY KEY
    ,parent INT
    ,elevation FLOAT
    ,localwatershed FLOAT
    ,inheritedwatershed FLOAT
    ,flow FLOAT
    ,contourIndex INT
    ,FOREIGN KEY (parent) REFERENCES RiverNodes(id)
    ,FOREIGN KEY (contourIndex) REFERENCES Shoreline(id)
);

SELECT
    AddGeometryColumn(
        'RiverNodes',
        'loc',
        347895,
        'POINT',
        'XY',
        1
    )
;

CREATE TABLE Qs (
    id INT PRIMARY KEY
    ,elevation FLOAT
);

SELECT
    AddGeometryColumn(
        'Qs',
        'loc',
        347895,
        'POINT',
        'XY',
        1
    )
;

CREATE TABLE Cells (
    rivernode INT
    ,polygonOrder INT
    ,q INT
    ,FOREIGN KEY (rivernode) REFERENCES RiverNodes(id)
    ,FOREIGN KEY (q) REFERENCES Qs(id)
);

CREATE TABLE Ts (
    id INT PRIMARY KEY
    ,rivercell INT
    ,elevation FLOAT
    ,FOREIGN KEY (rivercell) REFERENCES RiverNodes(id)
);

SELECT
    AddGeometryColumn(
        'Ts',
        'loc',
        347895,
        'POINT',
        'XY',
        1
    )
;

CREATE TABLE Edges (
    id INT PRIMARY KEY
    ,q0 INT
    ,q1 INT
    ,hasRiver BOOLEAN
    ,isShore BOOLEAN
    ,shore0 INT
    ,shore1 INT
    ,FOREIGN KEY (q0) REFERENCES Qs(id)
    ,FOREIGN KEY (q1) REFERENCES Qs(id)
    ,FOREIGN KEY (shore0) REFERENCES Shoreline(id)
    ,FOREIGN KEY (shore1) REFERENCES Shoreline(id)
);

CREATE TABLE RiverPaths (
    id INT PRIMARY KEY
    ,rivernode INT
    ,FOREIGN KEY (rivernode) REFERENCES RiverNodes(id)
);

SELECT
    AddGeometryColumn(
        'RiverPaths',
        'path',
        347895,
        'LINESTRING',
        'XYZ',
        1
    )
;

-- TODO: This table probably shouldn't be needed
CREATE TABLE Parameters (
    key TEXT PRIMARY KEY
    ,value TEXT
);

-- Views, functions, triggers, stored procedures, etc

-- get all the edges that are between children and parents
CREATE VIEW DownstreamEdges AS
SELECT
    nodes.id AS nodeID
    ,Edges.id AS downstreamEdgeID
FROM
    RiverNodes AS nodes
    JOIN Cells AS childQ0 ON childQ0.rivernode = nodes.id
    JOIN Cells AS childQ1 ON childQ1.rivernode = nodes.id
    JOIN Cells AS parentQ0 ON parentQ0.q = childQ0.q AND parentQ0.rivernode = nodes.parent
    JOIN Cells AS parentQ1 ON parentQ1.q = childQ1.q AND parentQ1.rivernode = nodes.parent
    JOIN Edges ON Edges.q0 = childQ0.q AND Edges.q1 = childQ1.q
;