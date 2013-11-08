var width = 1024,
    height = 860;

var quantize = d3.scale.quantize()
    .domain([0, .15])
    .range(d3.range(6).map(function(i) {
      return "q" + i + "-9"; }));

var projection = d3.geo.albers()
    .center([31.4, 0])
    .rotate([0, -1, -1])
    .parallels([0, 0.1])
    .scale(1200 * 7)
    .translate([width / 2, height / 2]);

var path = d3.geo.path()
    .projection(projection);

var svg = d3.select("body").append("svg")
    .attr("width", width)
    .attr("height", height);

  queue()
    .defer(d3.json, "/static/map_resources/uganda-district.json")
    .defer(d3.json, "/survey/3/completion/json/")
    .await(ready)

function get_class_color(rate_value)
{
    return "q" + rate_value + "-9";
}

function get_rate_color(rate){
    if (typeof(rate) == "undefined") return 5;
    if (rate >= 0 && rate< 20) return 0
    if (rate >= 20 && rate <= 40) return 1
    if (rate > 40 && rate <= 60) return 2;
    if (rate > 60 && rate <= 80) return 3;
    if (rate > 80 && rate <= 100) return 4;
    return 0;
}

function ready(error, geoJson, completionRates) {
  console.log(arguments);
  svg.append("g")
      .attr("class", "districts")
    .selectAll("path")
      .data(topojson.feature(geoJson, geoJson.objects.districts).features)
    .enter().append("path")
      .attr("class", function(d) {
        var rate = completionRates[(d.properties.name.toUpperCase())];
        return get_class_color(get_rate_color(rate));
      })
      .attr("d", path)
}