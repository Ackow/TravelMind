import { City, Country, State, type ICity } from "country-state-city";
import tzLookup from "tz-lookup";

export const runtime = "nodejs";

// 加载包含全球 250+ 国家、140,000+ 个城市的完整数据库
const cities = City.getAllCities();
const countryNames = new Map(
  Country.getAllCountries().map((country) => [country.isoCode, country.name]),
);

function cityLabel(city: ICity): string {
  const state = State.getStateByCodeAndCountry(
    city.stateCode,
    city.countryCode,
  );
  return [city.name, state?.name, countryNames.get(city.countryCode)]
    .filter(Boolean)
    .join(" · ");
}

export async function GET(request: Request) {
  const query = new URL(request.url).searchParams
    .get("q")
    ?.trim()
    .toLocaleLowerCase();

  if (!query || query.length < 2) {
    return Response.json({ cities: [] });
  }

  const results = cities
    .filter((city) => cityLabel(city).toLocaleLowerCase().includes(query))
    .sort((left, right) => {
      const leftName = left.name.toLocaleLowerCase();
      const rightName = right.name.toLocaleLowerCase();
      const leftScore =
        leftName === query ? 0 : leftName.startsWith(query) ? 1 : 2;
      const rightScore =
        rightName === query ? 0 : rightName.startsWith(query) ? 1 : 2;
      return leftScore - rightScore || leftName.localeCompare(rightName);
    })
    .slice(0, 12)
    .map((city) => {
      const latitude = Number(city.latitude);
      const longitude = Number(city.longitude);
      return {
        id: [city.countryCode, city.stateCode, city.name, city.latitude].join(
          "-",
        ),
        name: city.name,
        label: cityLabel(city),
        countryCode: city.countryCode,
        stateCode: city.stateCode,
        timezone:
          Number.isFinite(latitude) && Number.isFinite(longitude)
            ? tzLookup(latitude, longitude)
            : null,
      };
    });

  return Response.json({ cities: results });
}
