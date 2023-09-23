#include "shore.hpp"

Shore::Shore() { }

Shore::Shore(std::vector<Point> contour) {
    // Convert the vector of points to a vector of cv::Points
    // use a for each loop
    for (Point point : contour) {
        // since these points come from Python ShoreModel.__getitem__(),
        // they are in the project coordinates already
        this->contour.push_back(cv::Point2f(point.x(), point.y()));
    }
}

double Shore::distanceToShore(float x, float y) {
    return cv::pointPolygonTest(
        contour,
        cv::Point2f(x, y),
        true
    );
}

Point Shore::operator[](size_t idx) {
    return Point(contour[idx].x,contour[idx].y);
}