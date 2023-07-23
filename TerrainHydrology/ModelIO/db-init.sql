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

-- Views, functions, triggers, etc

-- Note that spatialite does not support dynamically-created geometry in views. Thus, although
-- the ultimate intention for most of these views is to generate geometry, you'll have to do
-- that last step manually.

-- get the 2 nodes that each edge divides
CREATE VIEW EdgeCells AS
SELECT
    Edges.id AS edge
    ,cell0q0.rivernode AS node0
    ,cell1q0.rivernode AS node1
FROM
    Edges
    -- this join will get us all the cells that have q0
    JOIN Cells AS cell0q0 ON cell0q0.q = Edges.q0
    -- this join will get us all the cells that have both q0 and q1
    -- since this is an inner join, the only matching records will be those cells that have both q0 and q1
    -- this also rules out edges that are on the coastline
    JOIN Cells AS cell0q1 ON cell0q1.q = Edges.q1 AND cell0q1.rivernode = cell0q0.rivernode
    -- but now we also have to get the other node. it also has these 2 qs, but it isn't the last one
    JOIN Cells AS cell1q0 ON cell1q0.q = Edges.q0
    JOIN Cells AS cell1q1 ON cell1q1.q = Edges.q1 AND cell1q1.rivernode = cell1q0.rivernode
WHERE
    cell0q0.rivernode < cell1q0.rivernode
;

-- get all the edges that are between children and parents
CREATE VIEW DownstreamEdges AS
SELECT
    childNodes.id AS rivernode
    ,EdgeCells.edge AS downstreamEdge
FROM
    RiverNodes AS childNodes
    JOIN EdgeCells ON (EdgeCells.node0 = childNodes.id AND EdgeCells.node1 = childNodes.parent) OR (EdgeCells.node1 = childNodes.id AND EdgeCells.node0 = childNodes.parent)
;

CREATE VIEW EdgeWatershedDivisions AS
WITH RECURSIVE NodeAncestors(rivernode, ancestor) AS (
    -- the anchor members are just all nodes that have a parent
    SELECT
        RiverNodes.id AS rivernode
        ,RiverNodes.id AS ancestor -- the node is its own ancestor. That may not make sense, but it makes the following query easier
    FROM
        RiverNodes
    WHERE
        RiverNodes.parent IS NOT NULL

    UNION ALL

    -- given a river node and one of its ancestors, return a record with that ancestor's parent, if it exists
    SELECT
        NodeAncestors.rivernode AS rivernode
        ,ancestorOfAncestor.id AS ancestor
    FROM
        NodeAncestors
        JOIN RiverNodes AS ancestor ON ancestor.id = NodeAncestors.ancestor
        -- since this is an inner join, no records will be returned if this ancestor has no parent
        JOIN RiverNodes AS ancestorOfAncestor ON ancestorOfAncestor.id = ancestor.parent

    LIMIT 10000 -- TMP DEBUG for safety
)
SELECT
    Edges.id AS edge
    ,side0cells.ancestor AS watershed0
    ,side1cells.ancestor AS watershed1
FROM
    Edges
    JOIN EdgeCells ON EdgeCells.edge = Edges.id
    -- line up all the nodes that are on one side of the edge, down to its root
    JOIN NodeAncestors AS side0cells ON
        side0cells.rivernode = EdgeCells.node0
    -- only continue if this cell doesn't appear in the ancestor list of the other side
    -- determine this by looking for it, and if the join doesn't find it, then it isn't
    -- there
    LEFT JOIN NodeAncestors AS counterfactual0 ON
        counterfactual0.rivernode = EdgeCells.node1
        AND counterfactual0.ancestor = side0cells.ancestor
    -- for all the nodes that aren't in the intersection, all of the nodes are divided
    -- from all the others
    JOIN NodeAncestors AS side1cells ON
        side1cells.rivernode = EdgeCells.node1
    -- we also have to make sure that these cells aren't in the ancestor list of the other side
    LEFT JOIN NodeAncestors AS counterfactual1 ON
        counterfactual1.rivernode = EdgeCells.node0
        AND counterfactual1.ancestor = side1cells.ancestor
WHERE
    counterfactual0.ancestor IS NULL
    AND counterfactual1.ancestor IS NULL
;